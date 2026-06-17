"""Race-scenario simulation built on the core MCTS world model.

The core :class:`~core.world_model.simulation.MCTSSimulator` drives selection /
expansion / rollout / backpropagation; this module supplies the **pure,
synchronous** transition model it requires (no I/O in the rollout — a hard
constraint of the core engine) plus a reward that prefers track position and a
fast total race time.

The state is encoded in :class:`~core.world_model.types.State` variables and the
decision space in :class:`~core.world_model.types.Action`. The best path found
is projected back onto a typed :class:`~.models.SimScenario`.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.observability.logging import get_logger
from core.world_model.simulation import MCTSSimulator
from core.world_model.types import Action, ActionType, State

from .models import SimScenario, StintState, TyreCompound

logger = get_logger(__name__)

# Per-lap degradation by compound (wear added each lap on that rubber).
_DEG = {
    TyreCompound.SOFT: 0.030,
    TyreCompound.MEDIUM: 0.020,
    TyreCompound.HARD: 0.013,
    TyreCompound.INTERMEDIATE: 0.025,
    TyreCompound.WET: 0.022,
}
# Base clean-air lap time (s); strategy deltas are relative to this.
_BASE_LAP = 78.0
# Time lost serving a pit stop (pit lane delta + stationary).
_PIT_LOSS = 22.0
# Lap-time penalty per unit of tyre wear (worn rubber is slow).
_WEAR_PENALTY = 7.0


@dataclass
class _MCTSBudget:
    """Lightweight config object consumed via getattr by the core simulator."""

    mcts_max_iterations: int
    mcts_max_depth: int
    mcts_simulation_depth: int
    mcts_time_limit: float
    mcts_exploration_weight: float = 1.41


def _pit_action(compound: TyreCompound) -> Action:
    """Build a pit-stop action that switches to ``compound``."""
    return Action(
        name=f"pit_{compound.value}",
        action_type=ActionType.EXECUTE,
        parameters={"pit": True, "compound": compound.value},
        cost=_PIT_LOSS,
        description=f"Pit for {compound.value} tyres",
    )


_STAY = Action(name="stay", action_type=ActionType.WAIT, parameters={"mode": "stay"})
_PUSH = Action(name="push", action_type=ActionType.EXECUTE, parameters={"mode": "push"})
_CONSERVE = Action(
    name="conserve", action_type=ActionType.EXECUTE, parameters={"mode": "conserve"}
)


class RaceSimulator:
    """What-if race strategy explorer over a fixed look-ahead horizon."""

    def __init__(self, max_iterations: int = 120, horizon_laps: int = 12) -> None:
        self._budget = _MCTSBudget(
            mcts_max_iterations=max_iterations,
            mcts_max_depth=horizon_laps,
            mcts_simulation_depth=horizon_laps,
            mcts_time_limit=2.0,
        )
        self._horizon = horizon_laps

    # -- transition model (pure, synchronous) ------------------------------

    def _get_actions(self, state: State) -> list[Action]:
        """Enumerate legal strategy moves from ``state``."""
        if int(state.get("laps_remaining", 0)) <= 0:
            return []
        actions = [_STAY, _PUSH, _CONSERVE]
        # Only allow a fresh-tyre stop if we have not just pitted.
        if int(state.get("laps_on_tyre", 0)) >= 1:
            actions += [
                _pit_action(TyreCompound.SOFT),
                _pit_action(TyreCompound.MEDIUM),
                _pit_action(TyreCompound.HARD),
            ]
        return actions

    def _apply_action(self, state: State, action: Action) -> State:
        """Advance the race one lap under ``action`` and return the next state."""
        params = action.parameters
        compound = TyreCompound(state.get("compound", "medium"))
        wear = float(state.get("wear", 0.0))
        laps_on_tyre = int(state.get("laps_on_tyre", 0))
        position = float(state.get("position", 5))
        gap_ahead = float(state.get("gap_ahead", 2.0))
        elapsed = float(state.get("elapsed", 0.0))
        pit_count = int(state.get("pit_count", 0))

        lap_time = _BASE_LAP + _WEAR_PENALTY * wear

        if params.get("pit"):
            compound = TyreCompound(params["compound"])
            wear = 0.0
            laps_on_tyre = 0
            # Pit loss is neutralisation-aware: a VSC/SC makes the stop cheap.
            pit_loss = float(state.get("pit_loss", _PIT_LOSS))
            lap_time += pit_loss
            # Less track position is ceded when the field is bunched/slowed.
            position += 2.0 if pit_loss >= _PIT_LOSS else 0.6
            pit_count += 1
        else:
            mode = params.get("mode", "stay")
            if mode == "push":
                lap_time -= 1.4
                wear += _DEG[compound] * 1.5
                gap_ahead = max(0.0, gap_ahead - 0.6)
            elif mode == "conserve":
                lap_time += 0.8
                wear += _DEG[compound] * 0.6
                gap_ahead += 0.3
            else:
                wear += _DEG[compound]
            laps_on_tyre += 1
            # Closing the gap eventually yields a position.
            if gap_ahead <= 0.2 and position > 1:
                position -= 1.0
                gap_ahead = 1.5

        wear = min(1.0, wear)
        next_state = state.set("wear", wear)
        next_state.variables.update(
            {
                "compound": compound.value,
                "laps_on_tyre": laps_on_tyre,
                "position": position,
                "gap_ahead": gap_ahead,
                "elapsed": elapsed + lap_time,
                "laps_remaining": int(state.get("laps_remaining", 0)) - 1,
                "pit_count": pit_count,
            }
        )
        return next_state

    def _reward(self, state: State) -> float:
        """Higher is better: reward track position and penalise lost time/wear."""
        position = float(state.get("position", 10))
        elapsed = float(state.get("elapsed", 0.0))
        wear = float(state.get("wear", 0.0))
        return -position * 10.0 - elapsed * 0.05 - wear * 4.0

    # -- public API --------------------------------------------------------

    def _initial_state(self, stint: StintState, pit_loss: float) -> State:
        """Project the live belief state into the simulator's initial state."""
        horizon = min(self._horizon, max(1, stint.laps_remaining))
        return State(
            name=f"race:{stint.car_id}",
            variables={
                "compound": stint.compound.value,
                "wear": stint.tyre_wear,
                "laps_on_tyre": stint.tyre_age_laps,
                "position": float(stint.position),
                "gap_ahead": stint.gap_ahead_s
                if stint.gap_ahead_s is not None
                else 2.0,
                "elapsed": 0.0,
                "laps_remaining": horizon,
                "pit_count": 0,
                "pit_loss": pit_loss,
            },
        )

    async def explore(
        self, stint: StintState, pit_loss: float = _PIT_LOSS
    ) -> SimScenario | None:
        """Run MCTS from the current stint and return the best scenario.

        ``pit_loss`` lets the caller pass a neutralisation-aware stop cost so the
        simulator favours boxing under a VSC/SC when a free stop is available.
        """
        simulator = MCTSSimulator(
            get_actions=self._get_actions,
            apply_action=self._apply_action,
            reward_fn=self._reward,
            is_goal=lambda s: int(s.get("laps_remaining", 0)) <= 0,
            config=self._budget,
        )
        result = await simulator.search(self._initial_state(stint, pit_loss))
        if not result.best_path or result.best_path.length == 0:
            return None
        final = result.final_state
        return SimScenario(
            actions=[a.name for a in result.best_path.actions],
            expected_position=float(final.get("position", stint.position))
            if final
            else float(stint.position),
            expected_race_time_s=float(final.get("elapsed", 0.0)) if final else 0.0,
            reward=result.best_reward,
            probability=result.best_path.probability,
        )


__all__ = ["RaceSimulator"]
