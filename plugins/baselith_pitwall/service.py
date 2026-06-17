"""Pit-wall orchestration service — the integration seam.

Folds validated telemetry into per-car belief state, runs the decision pipeline
once per new lap (swarm field → MCTS scenario → FIA guardrail → NL render), and
fans confirmed recommendations out to SSE subscribers and a ring buffer. All
heavy collaborators are injected so the service stays unit-testable without a
running event loop or external infra.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import deque

from core.observability.logging import get_logger

from .agents import CONSERVE, PIT_PRESSURE, THERMAL_RISK, SwarmCoordinator
from .battle import BattleAnalyzer
from .config import PitwallConfig
from .events import RaceEventModel
from .fusion import FusionEngine, FusionInputs
from .guardrails import FIAGuardrail, RaceContext
from .history import HistoricalRecall
from .ingestion import SimulatedSource, TelemetryBus, TelemetrySource
from .intel import IntelSynthesizer
from .metrics import record_frame, record_recommendation, time_decision
from .ontology import IndicatorSet
from .models import (
    BattleForecast,
    PitwallStatus,
    RaceControlState,
    RaceControlStatus,
    RadioMessage,
    Recommendation,
    RecommendationKind,
    RivalCar,
    StintState,
    StrategyOutcome,
    TelemetryFrame,
    WeatherState,
)
from .montecarlo import MonteCarloRace
from .recommendations import RecommendationEngine
from .session_models import AuditAction, AuditRecord
from .simulation import RaceSimulator
from .store import PitwallStore

logger = get_logger(__name__)


class PitwallService:
    """Coordinates ingestion, the swarm, simulation, guardrails and recall."""

    def __init__(
        self,
        config: PitwallConfig | None = None,
        bus: TelemetryBus | None = None,
        swarm: SwarmCoordinator | None = None,
        simulator: RaceSimulator | None = None,
        guardrail: FIAGuardrail | None = None,
        history: HistoricalRecall | None = None,
        engine: RecommendationEngine | None = None,
        *,
        tenant_id: str = "default",
        session_id: str = "default",
        store: PitwallStore | None = None,
    ) -> None:
        self.config = config or PitwallConfig()
        self.tenant_id = tenant_id
        self.session_id = session_id
        self.store = store
        self.bus = bus or TelemetryBus(maxsize=self.config.queue_maxsize)
        self.swarm = swarm or SwarmCoordinator()
        self.simulator = simulator or RaceSimulator(
            max_iterations=self.config.sim_max_iterations,
            horizon_laps=self.config.sim_horizon_laps,
        )
        self.guardrail = guardrail or FIAGuardrail()
        self.history = history or HistoricalRecall(
            semantic_enabled=self.config.semantic_enabled,
            top_k=self.config.history_top_k,
        )
        self.engine = engine or RecommendationEngine(
            use_llm=self.config.use_llm,
            llm_model=self.config.llm_model,
            legal_compounds=FIAGuardrail.legal_dry_compounds(),
        )
        self.events = RaceEventModel()
        self.montecarlo = MonteCarloRace(self.events)
        self.fusion = FusionEngine(self.events)
        self.intel = IntelSynthesizer(
            use_llm=self.config.use_llm, model=self.config.llm_model
        )

        self._stints: dict[str, StintState] = {}
        self._compounds_used: dict[str, set[str]] = {}
        self._radio_cues: dict[str, set[str]] = {}
        self._weather = WeatherState()
        self._race_control = RaceControlState()
        self._rivals: dict[str, list[RivalCar]] = {}
        self._recs: deque[Recommendation] = deque(
            maxlen=self.config.recommendation_buffer
        )
        self._subscribers: set[asyncio.Queue[Recommendation]] = set()
        self._frames = 0
        self._emitted = 0

    # -- race-context setters ----------------------------------------------

    def set_weather(self, weather: WeatherState) -> None:
        """Update the session weather state (drives wet/dry crossover)."""
        self._weather = weather

    def set_race_control(self, status: RaceControlStatus, lap: int = 0) -> None:
        """Update the race-control flag (green/yellow/VSC/SC)."""
        self._race_control = RaceControlState(status=status, since_lap=lap)
        logger.info("pitwall_race_control", status=status.value)

    def set_rivals(self, car_id: str, rivals: list[RivalCar]) -> None:
        """Set the nearby competitors used for battle/undercut analysis."""
        self._rivals[car_id] = rivals

    @property
    def weather(self) -> WeatherState:
        """Current session weather state."""
        return self._weather

    @property
    def race_control(self) -> RaceControlState:
        """Current race-control state."""
        return self._race_control

    def battle_forecast(self, car_id: str) -> BattleForecast | None:
        """Battle forecast against the most relevant rival, if any."""
        stint = self._stints.get(car_id)
        rivals = self._rivals.get(car_id) or []
        if stint is None or not rivals:
            return None
        # Pick the closest rival by absolute gap.
        rival = min(rivals, key=lambda r: abs(r.gap_s))
        pit_loss = RaceEventModel.pit_loss(self._race_control.status)
        return BattleAnalyzer.forecast(stint, rival, pit_loss=pit_loss)

    def outcome(self, car_id: str) -> StrategyOutcome | None:
        """Monte-Carlo outcome distribution for a car's live strategy."""
        stint = self._stints.get(car_id)
        if stint is None:
            return None
        return self.montecarlo.outcome_distribution(stint, samples=150)

    def _fuse(self, car_id: str, signals: dict[str, float]) -> IndicatorSet | None:
        """Fuse every live source into the cross-source indicator set for a car."""
        stint = self._stints.get(car_id)
        if stint is None:
            return None
        return self.fusion.fuse(
            FusionInputs(
                stint=stint,
                weather=self._weather,
                race_control=self._race_control,
                swarm_signals=signals or self.swarm.observe(stint),
                radio_cues=self._radio_cues.get(car_id, set()),
                history_hits=[],
                battle=self.battle_forecast(car_id),
                has_rivals=bool(self._rivals.get(car_id)),
            )
        )

    def indicators(self, car_id: str) -> IndicatorSet | None:
        """The current fused, cross-source indicator set for a car."""
        return self._fuse(car_id, {})

    async def intelligence(self, car_id: str) -> str | None:
        """AI-synthesised intelligence brief over the fused indicators."""
        indicator_set = self.indicators(car_id)
        if indicator_set is None:
            return None
        return await self.intel.brief(indicator_set)

    # -- lifecycle ---------------------------------------------------------

    async def initialize(self, sources: list[TelemetrySource] | None = None) -> None:
        """Start the telemetry bus with injected sources (or the simulated default).

        The session manager injects the adapter chosen for the session; when no
        sources are passed the legacy simulated-source config flag still applies,
        preserving the zero-infra boot behaviour the prototype relied on.
        """
        if sources is None:
            sources = []
            if self.config.use_simulated_source:
                sources.append(
                    SimulatedSource(
                        total_laps=self.config.sim_total_laps,
                        tick_seconds=self.config.sim_tick_seconds,
                    )
                )
        self.bus.start(self._on_frame, sources)
        logger.info("pitwall_service_started", simulated=bool(sources))

    async def shutdown(self) -> None:
        """Stop ingestion and release subscribers."""
        await self.bus.stop()
        self._subscribers.clear()
        logger.info("pitwall_service_stopped")

    def add_source(self, source: TelemetrySource) -> None:
        """Attach an external telemetry source to the running bus."""
        self.bus.start(self._on_frame, [source])

    # -- multimodal radio --------------------------------------------------

    _RADIO_CUES = {
        PIT_PRESSURE: ("box", "pit", "tyres are gone", "tyres gone", "no grip"),
        THERMAL_RISK: ("engine", "temps", "overheating", "power unit", "derate"),
        CONSERVE: ("save", "manage", "conserve", "lift and coast", "fuel"),
    }

    async def ingest_radio(self, message: RadioMessage) -> Recommendation | None:
        """Fold a team-radio transmission into the pheromone field and re-evaluate.

        Keyword cues bias the swarm signals (a driver shouting "box, box" raises
        pit pressure), making the pit wall genuinely multimodal: numeric
        telemetry and natural-language radio share one decision substrate.
        """
        stint = self._stints.get(message.car_id)
        if stint is None:
            return None
        text = message.text.lower()
        field = self.swarm.colony.pheromones
        loc = f"car:{message.car_id}"
        cues_hit = self._radio_cues.setdefault(message.car_id, set())
        for signal, cues in self._RADIO_CUES.items():
            if any(cue in text for cue in cues):
                field.deposit(signal, loc, intensity=1.5, agent_id="radio")
                cues_hit.add(signal)
        rec = await self.evaluate(message.car_id)
        if rec is not None:
            await self._publish(rec)
        return rec

    # -- ingestion handler -------------------------------------------------

    async def _on_frame(self, frame: TelemetryFrame) -> None:
        """Fold a frame into belief state and evaluate on each new lap."""
        prev = self._stints.get(frame.car_id)
        deg = 0.0
        if prev is not None and frame.lap > prev.lap and frame.tyre_age_laps > 0:
            deg = max(0.0, (frame.tyre_wear - prev.tyre_wear))
        self._compounds_used.setdefault(frame.car_id, set()).add(frame.compound.value)
        stint = StintState(
            car_id=frame.car_id,
            lap=frame.lap,
            total_laps=self.config.sim_total_laps,
            position=frame.position,
            compound=frame.compound,
            tyre_age_laps=frame.tyre_age_laps,
            tyre_wear=frame.tyre_wear,
            deg_rate_per_lap=round(deg, 4),
            fuel_kg=frame.fuel_kg,
            engine_temp_c=frame.engine_temp_c,
            gap_ahead_s=frame.gap_ahead_s,
            gap_behind_s=frame.gap_behind_s,
        )
        self._stints[frame.car_id] = stint
        self._frames += 1
        record_frame(self.tenant_id)

        is_new_lap = prev is None or frame.lap > prev.lap
        if is_new_lap:
            if self.store is not None and self.config.persist_snapshots:
                await self.store.add_stint_snapshot(
                    self.tenant_id, self.session_id, stint
                )
            with time_decision(self.tenant_id):
                rec = await self.evaluate(frame.car_id)
            if rec is not None:
                await self._publish(rec)

    # -- decision pipeline -------------------------------------------------

    async def evaluate(self, car_id: str) -> Recommendation | None:
        """Run the full decision pipeline for one car; None if below threshold."""
        stint = self._stints.get(car_id)
        if stint is None:
            return None

        signals = self.swarm.observe(stint)
        # Neutralisation-aware pit loss biases the simulator toward a free stop.
        pit_loss = RaceEventModel.pit_loss(self._race_control.status)
        scenario = await self.simulator.explore(stint, pit_loss=pit_loss)
        battle = self.battle_forecast(car_id)
        outcome = self.outcome(car_id)
        candidate = self.engine.decide(
            stint,
            signals,
            scenario,
            weather=self._weather,
            race_control=self._race_control,
            battle=battle,
        )

        context = RaceContext(
            compounds_used=self._compounds_used.get(car_id, set()),
            is_dry=self._weather.is_dry,
            pit_compound=candidate.pit_compound,
        )
        verdict = self.guardrail.validate(candidate.kind, stint, context)

        query = (
            f"{candidate.kind.value} {stint.compound.value} wear {stint.tyre_wear:.1f}"
        )
        refs = await self.history.recall(query)

        rec = await self.engine.render(
            candidate,
            stint,
            scenario,
            signals,
            refs,
            verdict,
            battle=battle,
            outcome=outcome,
            race_control=self._race_control,
        )
        # Fuse every live source into the cross-source indicator set (Palantir-style).
        rec.indicators = self.fusion.fuse(
            FusionInputs(
                stint=stint,
                weather=self._weather,
                race_control=self._race_control,
                swarm_signals=signals,
                radio_cues=self._radio_cues.get(car_id, set()),
                history_hits=refs,
                battle=battle,
                has_rivals=bool(self._rivals.get(car_id)),
            )
        )
        self.swarm.decay()

        if rec.kind is not RecommendationKind.HOLD and rec.confidence < (
            self.config.min_confidence
        ):
            return None
        self._recs.append(rec)
        self._emitted += 1
        record_recommendation(self.tenant_id, rec.kind.value)
        if self.store is not None:
            await self.store.save_recommendation(self.tenant_id, self.session_id, rec)
            await self._audit(
                AuditAction.RECOMMENDATION_EMITTED,
                car_id=rec.car_id,
                detail={"kind": rec.kind.value, "confidence": rec.confidence},
            )
        return rec

    # -- audit -------------------------------------------------------------

    async def _audit(
        self,
        action: AuditAction,
        *,
        actor: str = "system",
        car_id: str | None = None,
        detail: dict[str, object] | None = None,
    ) -> None:
        """Append an audit record to the store (no-op without a store)."""
        if self.store is None:
            return
        await self.store.add_audit(
            AuditRecord(
                id=uuid.uuid4().hex,
                tenant_id=self.tenant_id,
                session_id=self.session_id,
                actor=actor,
                action=action,
                car_id=car_id,
                detail=detail or {},
            )
        )

    async def record_audit(
        self,
        action: AuditAction,
        *,
        actor: str,
        car_id: str | None = None,
        detail: dict[str, object] | None = None,
    ) -> None:
        """Public hook for routers to record an actor-attributed context change."""
        await self._audit(action, actor=actor, car_id=car_id, detail=detail)

    # -- pub/sub -----------------------------------------------------------

    async def _publish(self, rec: Recommendation) -> None:
        """Fan a recommendation out to all live SSE subscribers."""
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(rec)
            except asyncio.QueueFull:  # pragma: no cover - slow consumer guard
                logger.debug("pitwall_subscriber_lagging")

    def subscribe(self) -> asyncio.Queue[Recommendation]:
        """Register a new SSE subscriber queue."""
        queue: asyncio.Queue[Recommendation] = asyncio.Queue(maxsize=64)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Recommendation]) -> None:
        """Remove an SSE subscriber queue."""
        self._subscribers.discard(queue)

    # -- read surface ------------------------------------------------------

    def status(self, version: str) -> PitwallStatus:
        """Aggregate health snapshot."""
        return PitwallStatus(
            version=version,
            running=self.bus.running,
            cars_tracked=len(self._stints),
            frames_ingested=self.bus.frames_ingested,
            recommendations_emitted=self._emitted,
            queue_depth=self.bus.depth(),
            swarm_agents=self.swarm.agent_count,
            llm_enabled=self.config.use_llm,
            semantic_enabled=self.config.semantic_enabled,
        )

    def get_stint(self, car_id: str) -> StintState | None:
        """Return the current belief state for a car, if tracked."""
        return self._stints.get(car_id)

    def list_cars(self) -> list[str]:
        """All car ids currently tracked."""
        return sorted(self._stints)

    def recent_recommendations(
        self, car_id: str | None = None, limit: int = 50
    ) -> list[Recommendation]:
        """Most-recent recommendations, optionally filtered by car."""
        items = [r for r in self._recs if car_id is None or r.car_id == car_id]
        return list(reversed(items))[:limit]


__all__ = ["PitwallService"]
