"""
Interview flow handler.

Translates one patient turn into:
    1. NER extraction → graph upsert (LLM + heuristic fallback).
    2. Red-flag evaluation. Positive match short-circuits the loop with an
       ``escalate=True`` payload that callers (router, orchestrator) must
       surface to a human immediately.
    3. **Live differential preview** — once the graph holds at least one
       symptom, the agent runs a cheap heuristic ranking so the UI can
       display a draft DDx without waiting for the final ``/triage/finalize``
       call. The LLM ranking is invoked on a sliding cadence to keep the
       turn snappy on small models.
    4. Next empathic question.

The handler exposes a ``handle(query, context) -> dict`` signature compatible
with the core ``FlowHandler`` protocol.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from core.observability.logging import get_logger
from core.plugins.result import ok

from ..agents.anamnesis_agent import AnamnesisAgent
from ..agents.clinical_reasoner import ClinicalReasoner, ReasonerUnavailable
from ..agents.differential_dx_agent import (
    DifferentialDxAgent,
    _CHARACTER_KEYWORDS,
    _RADIATION_REGEX,
    _infer_onset,
    _infer_severity,
    detect_subject_denials,
    extract_allergies,
    extract_medications,
    extract_modifiers,
    extract_risk_factors,
    is_global_denial,
    select_discriminator_question,
)
from ..graph.repository import SymptomGraphRepository
from ..models.clinical import DifferentialDiagnosis, ReportStatus, TriageReport
from ..models.triage import TriageEngine
from ..safety.redflags import RedFlagEvaluator
from .intake_report import render_intake_report

logger = get_logger(__name__)


class InterviewFlowHandler:
    """One turn of the empathic interview loop with live DDx preview."""

    # Heuristic preview runs every turn (cheap); LLM ranking is only invoked
    # at finalize to keep turn latency low on small models.
    PREVIEW_HYPOTHESES_LIMIT = 5
    # Hard cap on interview turns (matches the appoint-ready 20-Q ceiling).
    # When exceeded the next turn auto-finalizes regardless of remaining slots.
    MAX_QUESTIONS = 20

    def __init__(
        self,
        *,
        anamnesis_agent: AnamnesisAgent,
        dx_agent: DifferentialDxAgent,
        graph: SymptomGraphRepository,
        red_flags: RedFlagEvaluator | None = None,
        triage_engine: TriageEngine | None = None,
        triage_handler: Any = None,
        reasoner: ClinicalReasoner | None = None,
        use_reasoner: bool = False,
    ) -> None:
        self._anamnesis = anamnesis_agent
        self._dx = dx_agent
        self._graph = graph
        self._red_flags = red_flags or RedFlagEvaluator()
        self._triage = triage_engine or TriageEngine()
        self._triage_handler = triage_handler
        # Hypothesis-driven reasoner. When ``use_reasoner`` is set and the
        # reasoner is available, it drives the interview; on any LLM failure
        # the loop falls back to the deterministic OPQRST/discriminator path.
        self._reasoner = reasoner
        self._use_reasoner = use_reasoner and reasoner is not None

    def set_triage_handler(self, handler: Any) -> None:
        """Late-bind the triage handler used for inline finalize."""
        self._triage_handler = handler

    async def handle(
        self,
        query: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        session_id = str(context.get("session_id") or uuid4())
        turn_id = str(context.get("turn_id") or uuid4())

        self._graph.record_patient_turn(session_id, query)
        # Read the slot the agent probed last turn — interpreting short
        # "no/nessuno" replies against this slot is how we satisfy
        # allergies/medications/PMH without forcing the loop to re-ask twice.
        prev_snap = self._graph.snapshot(session_id)
        last_slot = prev_snap.last_target_slot
        # If the previous turn asked a discriminator question, attach the
        # current utterance as the answer so the clinician sees the full
        # yes/no in the report instead of an orphan question.
        if last_slot and last_slot.startswith("discriminator:"):
            self._graph.attach_discriminator_answer(
                session_id,
                key=last_slot.split(":", 1)[1],
                answer=query,
            )

        observation = await self._dx.extract_entities(
            query, turn_id=turn_id, last_question_slot=last_slot
        )
        self._graph.merge_observation(session_id, observation)

        # Always promote slot fillers parsed from the utterance onto the most
        # recently added symptom: the patient often answers follow-ups with
        # metadata only (``stamattina``, ``NRS 8``), and the LLM can also
        # hallucinate a symptom name when the utterance carries none, which
        # would otherwise mask the real onset/severity reported by the user.
        lower_query = query.lower()
        extra_character = [c for c in _CHARACTER_KEYWORDS if c in lower_query]
        if _RADIATION_REGEX.search(lower_query) and "irradia" not in extra_character:
            extra_character.append("irradia")
        # Modifier verbs (``peggiora``, ``allevia``, ``aggrava`` ...) capture
        # what makes the symptom worse or better. Prefixed entries
        # (``peggiora: ...`` / ``migliora: ...``) hit the existing slot-fill
        # predicate so the agent stops re-asking the modifiers slot when
        # the patient has already answered it in free text.
        modifier_entries = extract_modifiers(lower_query)
        if modifier_entries:
            extra_character.extend(modifier_entries)
        self._graph.enrich_recent_symptom(
            session_id,
            onset=_infer_onset(query),
            severity_nrs=_infer_severity(query),
            character=extra_character or None,
        )
        if modifier_entries:
            self._graph.satisfy_slot(session_id, "modifiers")

        # Pull structured anamnestic data (allergies / meds / PMH) from the
        # utterance and route it into the snapshot so the slot machinery
        # sees real evidence. Heuristic-only — no LLM round-trip.
        allergies_found = extract_allergies(lower_query)
        if allergies_found:
            self._graph.record_allergies(session_id, allergies_found)
            self._graph.satisfy_slot(session_id, "allergies")
        meds_found = extract_medications(lower_query)
        if meds_found:
            self._graph.record_medications(session_id, meds_found)
            self._graph.satisfy_slot(session_id, "medications")
        pmh_found = extract_risk_factors(lower_query)
        if pmh_found:
            self._graph.record_risk_factors(session_id, pmh_found)
            self._graph.satisfy_slot(session_id, "past_medical_history")

        # Patient gave a global "no/niente" reply targeting the slot the
        # agent just probed → mark slot satisfied so the loop advances.
        if last_slot and is_global_denial(query):
            self._graph.satisfy_slot(session_id, last_slot)
            # Persist denial-as-data so the clinician sees the negative.
            if last_slot == "allergies":
                self._graph.record_allergies(session_id, ["nessuna nota"])
            elif last_slot == "medications":
                self._graph.record_medications(session_id, ["nessuno"])
            elif last_slot == "past_medical_history":
                self._graph.record_risk_factors(session_id, ["nessuna patologia nota"])

        # Subject-aware denials handle out-of-turn replies like "nessun
        # farmaco" even if the agent just asked something different.
        subject_denied = detect_subject_denials(lower_query)
        if subject_denied:
            current = self._graph.snapshot(session_id)
            for slot in subject_denied:
                self._graph.satisfy_slot(session_id, slot)
                if slot == "medications" and not current.medications:
                    self._graph.record_medications(session_id, ["nessuno"])
                elif slot == "allergies" and not current.allergies:
                    self._graph.record_allergies(session_id, ["nessuna nota"])
                elif slot == "past_medical_history" and not current.risk_factors:
                    self._graph.record_risk_factors(
                        session_id, ["nessuna patologia nota"]
                    )

        evaluation = self._red_flags.evaluate(self._graph, session_id)
        snap = self._graph.snapshot(session_id)

        if evaluation.requires_immediate_escalation:
            envelope = ok(
                data={
                    "session_id": session_id,
                    "escalate": True,
                    "triage_code": "RED",
                    "reason": evaluation.summary,
                    "instruction": (
                        "Indirizza il paziente immediatamente al 118 o al "
                        "Pronto Soccorso più vicino."
                    ),
                    "known_symptoms": [s.canonical_name for s in snap.symptoms],
                    "matrix": snap.to_matrix(red_flags=evaluation.matches).model_dump(
                        mode="json"
                    ),
                    "preview": self._build_preview(snap, evaluation.matches),
                },
                message="Red flag clinico rilevato.",
                metadata={"requires_human": True, "session_id": session_id},
            )
            return envelope.model_dump(mode="json")

        # Enforce hard cap on interview length: past MAX_QUESTIONS we auto-
        # finalize even if slots are still empty. The appoint-ready guideline
        # is to cap probing once data is good enough so the clinician is not
        # kept waiting on diminishing returns.
        turn_count = len(snap.asked_questions)
        if (
            turn_count >= self.MAX_QUESTIONS
            and self._triage_handler is not None
            and snap.symptoms
        ):
            return await self._finalize_inline(
                context=context,
                session_id=session_id,
                question_text=(
                    "Grazie. Anamnesi completata: il pre-triage è "
                    "pronto per la validazione del medico."
                ),
                tone="reassuring",
                evaluation_matches=evaluation.matches,
                snap=snap,
            )

        # Hypothesis-driven reasoner path. When enabled and the LLM is
        # reachable, it maintains a live differential and chooses the next
        # question that discriminates it best — instead of walking the fixed
        # OPQRST slot list. Any LLM failure raises ReasonerUnavailable and we
        # fall through to the deterministic discriminator/OPQRST path below.
        if self._use_reasoner and self._reasoner is not None and snap.symptoms:
            try:
                return await self._reasoner_turn(
                    context=context,
                    session_id=session_id,
                    turn_id=turn_id,
                    snap=snap,
                    evaluation_matches=evaluation.matches,
                )
            except ReasonerUnavailable:
                logger.info("Reasoner unavailable; using deterministic path.")

        # Try a condition-specific discriminator BEFORE the generic LLM
        # anamnesis question. When the heuristic DDx shows two close-ranked
        # hypotheses, a single yes/no probe (e.g. "Ha fotofobia?") cuts the
        # differential more sharply than another OPQRST slot. This mirrors
        # the appoint-ready "probe high-yield clues" guideline.
        heuristic_ddx = self._dx._heuristic_rank(  # noqa: SLF001 — fast path
            snap.to_matrix(red_flags=evaluation.matches)
        )
        discriminator = select_discriminator_question(
            heuristic_ddx,
            already_asked=set(snap.discriminators_asked),
        )
        if discriminator is not None and snap.symptoms:
            q_text, q_key, condition = discriminator
            self._graph.record_discriminator(
                session_id, key=q_key, question=q_text, condition=condition
            )
            target_slot = f"discriminator:{q_key}"
            self._graph.record_question(session_id, q_text)
            self._graph.set_last_target_slot(session_id, target_slot)
            slots_total = 12
            slots_unfilled = len(self._graph.find_unfilled_slots(session_id))
            progress = 1 - (slots_unfilled / slots_total)
            preview = self._build_preview(snap, evaluation.matches)
            envelope = ok(
                data={
                    "session_id": session_id,
                    "question": q_text,
                    "target_slot": target_slot,
                    "tone": "empathic",
                    "rationale": f"discriminante {condition}",
                    "progress": round(progress, 2),
                    "known_symptoms": [s.canonical_name for s in snap.symptoms],
                    "matrix": snap.to_matrix(red_flags=evaluation.matches).model_dump(
                        mode="json"
                    ),
                    "preview": preview,
                },
                message="Domanda discriminante differenziale.",
                metadata={"session_id": session_id, "turn_id": turn_id},
            )
            return envelope.model_dump(mode="json")

        next_q = await self._anamnesis.next_question(session_id, last_utterance=query)
        # Honor an explicit ``End interview.`` sentinel from the LLM (matches
        # appoint-ready convention) — route straight to finalize.
        is_end_sentinel = "end interview" in next_q.text.lower().strip(" .!?")
        if (is_end_sentinel or next_q.target_slot == "finalize") and (
            self._triage_handler is not None and snap.symptoms
        ):
            return await self._finalize_inline(
                context=context,
                session_id=session_id,
                question_text=(
                    "Grazie. Anamnesi completata: il pre-triage è "
                    "pronto per la validazione del medico."
                ),
                tone=next_q.tone or "reassuring",
                evaluation_matches=evaluation.matches,
                snap=snap,
            )

        # Count the ask so the same slot is not pursued indefinitely when the
        # patient cannot provide it: after 2 unanswered attempts the slot is
        # marked skipped and the next gap is targeted.
        if next_q.target_slot and next_q.target_slot != "finalize":
            self._graph.bump_slot_ask(session_id, next_q.target_slot, max_asks=2)
        # Persist the question we are about to return so the next turn can
        # see it in the conversational memory and avoid re-asking. Also
        # remember the slot under probe so a short "no" reply lands in the
        # right place.
        self._graph.record_question(session_id, next_q.text)
        self._graph.set_last_target_slot(session_id, next_q.target_slot)
        slots_total = 12
        slots_unfilled = len(self._graph.find_unfilled_slots(session_id))
        progress = 1 - (slots_unfilled / slots_total)

        preview = self._build_preview(snap, evaluation.matches)
        envelope = ok(
            data={
                "session_id": session_id,
                "question": next_q.text,
                "target_slot": next_q.target_slot,
                "tone": next_q.tone,
                "rationale": next_q.rationale,
                "progress": round(progress, 2),
                "known_symptoms": [s.canonical_name for s in snap.symptoms],
                "matrix": snap.to_matrix(red_flags=evaluation.matches).model_dump(
                    mode="json"
                ),
                "preview": preview,
            },
            message="Next interview turn ready.",
            metadata={"session_id": session_id, "turn_id": turn_id},
        )
        return envelope.model_dump(mode="json")

    async def _reasoner_turn(
        self,
        *,
        context: dict[str, Any],
        session_id: str,
        turn_id: str,
        snap: Any,
        evaluation_matches: list[str],
    ) -> dict[str, Any]:
        """One hypothesis-driven turn. Raises ReasonerUnavailable to fall back.

        The reasoner returns a live differential plus the next discriminating
        question (or a finalize signal). The differential it produces seeds
        both the live preview and the inline finalize, replacing the heuristic
        baseline whenever the LLM is reachable.
        """
        assert self._reasoner is not None  # guarded by caller
        dialogue = self._graph.recent_dialogue(session_id, last_n=6)
        matrix = snap.to_matrix(red_flags=evaluation_matches)
        turn = await self._reasoner.deliberate(
            matrix=matrix,
            dialogue=dialogue,
            asked_questions=list(snap.asked_questions),
        )
        reasoner_ddx = DifferentialDiagnosis(
            hypotheses=list(turn.differential),
            model_id=self._reasoner.model_id,
            notes=turn.reasoning_note or None,
        )

        if turn.ready_to_finalize and self._triage_handler is not None:
            return await self._finalize_inline(
                context=context,
                session_id=session_id,
                question_text=(
                    "Grazie. Anamnesi completata: il pre-triage è "
                    "pronto per la validazione del medico."
                ),
                tone="reassuring",
                evaluation_matches=evaluation_matches,
                snap=snap,
                reasoner_ddx=reasoner_ddx,
            )

        question = turn.next_question
        if question is None:
            # Not finalizing yet but no question to ask → treat as a miss and
            # let the deterministic path pick the next slot.
            raise ReasonerUnavailable("no next question and not finalizing")

        self._graph.record_question(session_id, question.text)
        self._graph.set_last_target_slot(session_id, "reasoner")
        turn_count = len(snap.asked_questions)
        progress = min(0.95, turn_count / self.MAX_QUESTIONS)
        rationale = question.rationale or (
            f"probe: {question.probes_for}"
            if question.probes_for
            else "ragionamento clinico"
        )
        preview = self._build_preview(
            snap, evaluation_matches, reasoner_ddx=reasoner_ddx
        )
        envelope = ok(
            data={
                "session_id": session_id,
                "question": question.text,
                "target_slot": "reasoner",
                "tone": question.tone,
                "rationale": rationale,
                "progress": round(progress, 2),
                "known_symptoms": [s.canonical_name for s in snap.symptoms],
                "matrix": matrix.model_dump(mode="json"),
                "preview": preview,
            },
            message="Domanda clinica ipotesi-driven.",
            metadata={
                "session_id": session_id,
                "turn_id": turn_id,
                "reasoner": True,
            },
        )
        return envelope.model_dump(mode="json")

    async def _finalize_inline(
        self,
        *,
        context: dict[str, Any],
        session_id: str,
        question_text: str,
        tone: str,
        evaluation_matches: list[str],
        snap: Any,
        reasoner_ddx: DifferentialDiagnosis | None = None,
    ) -> dict[str, Any]:
        """Finalize the interview synchronously using the heuristic ranker.

        The full ``/triage/finalize`` endpoint still runs the LLM-backed
        ranker; this inline path is invoked automatically when the agent
        decides it is done and must return *fast* — a slow LLM call here
        leaves the patient staring at the typing indicator. The clinician
        gets the same payload shape (so the UI doesn't branch) but built
        from the deterministic ranking + intake renderer.
        """
        del context
        pseudonym = f"pt-{session_id[:8]}"
        matrix = snap.to_matrix(red_flags=evaluation_matches)
        # Prefer the reasoner's accumulated differential; fall back to the
        # deterministic ranker when the reasoner is off or was unavailable.
        ddx = (
            reasoner_ddx
            if reasoner_ddx is not None and reasoner_ddx.hypotheses
            else self._dx._heuristic_rank(matrix)  # noqa: SLF001 — fast path
        )
        decision = self._triage.classify(matrix, ddx)
        intake_md = render_intake_report(
            matrix,
            medications=list(snap.medications),
            risk_factors=list(snap.risk_factors),
            allergies=list(snap.allergies),
            differential=ddx,
            triage=decision.model_dump(mode="json"),
            discriminator_answers=list(snap.discriminator_answers),
            patient_pseudonym=pseudonym,
            session_id=session_id,
        )
        report = TriageReport(
            session_id=session_id,
            patient_pseudonym=pseudonym,
            symptom_matrix=matrix,
            differential=ddx,
            triage=decision.model_dump(mode="json"),
            status=ReportStatus.PENDING_VALIDATION,
            intake_report=intake_md,
        )
        triage_data = report.model_dump(mode="json")
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "question": question_text,
                "target_slot": "finalize",
                "tone": tone,
                "progress": 1.0,
                "known_symptoms": [s.canonical_name for s in snap.symptoms],
                "matrix": snap.to_matrix(red_flags=evaluation_matches).model_dump(
                    mode="json"
                ),
                "preview": triage_data,
                "auto_finalized": True,
            },
            "metadata": {"session_id": session_id, "auto_finalized": True},
            "message": "Anamnesi completata; report generato.",
        }

    def _build_preview(
        self,
        snap,
        red_flags: list[str],
        *,
        reasoner_ddx: DifferentialDiagnosis | None = None,
    ) -> dict[str, Any] | None:
        """Build a live preview of the differential the clinician is watching.

        Uses the reasoner's live differential when supplied; otherwise the
        deterministic heuristic ranking (no LLM call). The preview never
        claims to be final.
        """
        matrix = snap.to_matrix(red_flags=red_flags)
        if not matrix.symptoms and not matrix.denied_symptoms:
            return None
        ddx = (
            reasoner_ddx
            if reasoner_ddx is not None
            else self._dx._heuristic_rank(matrix)  # noqa: SLF001 — internal helper
        )
        ddx = ddx.model_copy(
            update={"hypotheses": ddx.hypotheses[: self.PREVIEW_HYPOTHESES_LIMIT]}
        )
        decision = self._triage.classify(matrix, ddx)
        intake = render_intake_report(
            matrix,
            medications=list(snap.medications),
            risk_factors=list(snap.risk_factors),
            allergies=list(snap.allergies),
            differential=ddx,
            triage=decision.model_dump(mode="json"),
            discriminator_answers=list(snap.discriminator_answers),
        )
        return {
            "is_preview": True,
            "differential": ddx.model_dump(mode="json"),
            "triage": decision.model_dump(mode="json"),
            "symptom_count": len(matrix.symptoms),
            "red_flag_count": len(matrix.red_flags),
            "denied_symptoms": list(matrix.denied_symptoms),
            "intake_report": intake,
        }
