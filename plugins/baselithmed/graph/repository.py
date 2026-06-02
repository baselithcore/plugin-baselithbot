"""
In-process Symptom Graph repository.

Acts as a stand-in for the production GraphDb (FalkorDB/RedisGraph) wrapper so
the rest of the plugin can be exercised without external infrastructure.
The public surface (``merge_observation``, ``snapshot``, ``find_unfilled_slots``)
is deliberately small and stable; swapping the backend for the real
:class:`core.graph.GraphDb` is a single-file change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Final

from ..models.clinical import (
    ExtractedObservation,
    Symptom,
    SymptomMatrix,
    TemporalLink,
)

ANAMNESIS_SLOTS: Final[tuple[str, ...]] = (
    "chief_complaint",
    "onset",
    "location",
    "character",
    "radiation",
    "severity",
    "timing",
    "modifiers",
    "associated_symptoms",
    "past_medical_history",
    "allergies",
    "medications",
)

# Symptom name fragments that mark a localizable (body-site-bearing)
# complaint. Pain/ache words + body parts. When NO symptom in the session
# is localizable, the ``location`` and ``radiation`` OPQRST slots are
# irrelevant (e.g. "apnea notturna", "insonnia", "febbre") and are skipped
# so the interview never asks "where do you feel your sleep apnea?".
_LOCALIZABLE_FRAGMENTS: Final[tuple[str, ...]] = (
    "dolore",
    "mal di",  # mal di testa, mal di pancia, mal di schiena
    "male",
    "algia",  # cervicalgia, lombalgia, mialgia, nevralgia...
    "cefal",  # cefalea
    "toracic",
    "addominal",
    "lombalg",
    "cervicalg",
    "oculare",
    "rigidità",
    "gonfiore",
    "tumefazion",
    "eruzione",
    "rash",
    "lesion",
    "ferita",
    "frattura",
    "trauma",
    "contusion",
    "bruciore",
    "prurito",
    "formicol",
    "crampo",
    "crampi",
)


def _is_localizable(canonical_name: str, raw_quote: str | None) -> bool:
    """``True`` when a symptom plausibly maps to a body location."""
    hay = f"{canonical_name} {raw_quote or ''}".lower()
    return any(frag in hay for frag in _LOCALIZABLE_FRAGMENTS)


@dataclass
class SymptomGraphSnapshot:
    """A read-only view of the graph for a single session."""

    session_id: str
    symptoms: list[Symptom] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    temporal_links: list[TemporalLink] = field(default_factory=list)
    slot_ask_count: dict[str, int] = field(default_factory=dict)
    skipped_slots: set[str] = field(default_factory=set)
    # Slots the patient has *explicitly satisfied* (e.g. answered ``"no,
    # nessun farmaco"``) — these count as filled even when the underlying
    # list stays empty. Without this the loop re-asks "Sta assumendo
    # farmaci?" forever because ``snap.medications`` is empty.
    satisfied_slots: set[str] = field(default_factory=set)
    asked_questions: list[str] = field(default_factory=list)
    patient_turns: list[str] = field(default_factory=list)
    # Last slot the agent asked the patient about. Used to interpret short
    # "no"/"niente" answers as a denial targeting that slot.
    last_target_slot: str | None = None
    # Pertinent negatives: canonical symptom names the patient denied.
    denied_symptoms: list[str] = field(default_factory=list)
    # Discriminator probes already asked this session. Keyed by the short
    # discriminator key, e.g. ``"emicrania_fotofobia"``. Used to avoid
    # repeating a condition-specific question across turns.
    discriminators_asked: set[str] = field(default_factory=set)
    # Discriminator answers — one entry per probe asked. Captured verbatim
    # so the clinician sees what was claimed without re-reading the chat.
    discriminator_answers: list[dict[str, str]] = field(default_factory=list)

    def to_matrix(self, red_flags: list[str] | None = None) -> SymptomMatrix:
        return SymptomMatrix(
            symptoms=list(self.symptoms),
            temporal_sequence=list(self.temporal_links),
            red_flags=list(red_flags or []),
            denied_symptoms=list(self.denied_symptoms),
            medications=list(self.medications),
            allergies=list(self.allergies),
            past_medical_history=list(self.risk_factors),
        )


class SymptomGraphRepository:
    """Thread-safe, per-session symptom graph storage."""

    def __init__(self) -> None:
        self._sessions: dict[str, SymptomGraphSnapshot] = {}
        self._lock = RLock()

    def _ensure(self, session_id: str) -> SymptomGraphSnapshot:
        snap = self._sessions.get(session_id)
        if snap is None:
            snap = SymptomGraphSnapshot(session_id=session_id)
            self._sessions[session_id] = snap
        return snap

    def merge_observation(
        self,
        session_id: str,
        observation: ExtractedObservation,
    ) -> None:
        """Idempotently upsert an extracted observation into the graph.

        Dedup is on ``canonical_name`` alone (a single body site per symptom
        is enough for triage). When a later turn brings new metadata
        (onset, severity, body site, character) the existing node is
        updated rather than duplicated.
        """
        with self._lock:
            snap = self._ensure(session_id)
            by_name: dict[str, int] = {
                s.canonical_name: idx for idx, s in enumerate(snap.symptoms)
            }
            for symptom in observation.symptoms:
                idx = by_name.get(symptom.canonical_name)
                if idx is None:
                    snap.symptoms.append(symptom)
                    by_name[symptom.canonical_name] = len(snap.symptoms) - 1
                    continue
                existing = snap.symptoms[idx]
                merged_character = list(
                    dict.fromkeys([*existing.character, *symptom.character])
                )
                snap.symptoms[idx] = existing.model_copy(
                    update={
                        "body_site": existing.body_site or symptom.body_site,
                        "onset": existing.onset or symptom.onset,
                        "severity_nrs": existing.severity_nrs
                        if existing.severity_nrs is not None
                        else symptom.severity_nrs,
                        "character": merged_character,
                        "icd10_hint": existing.icd10_hint or symptom.icd10_hint,
                    }
                )
            for med in observation.medications:
                if med not in snap.medications:
                    snap.medications.append(med)
            for rf in observation.risk_factors:
                if rf not in snap.risk_factors:
                    snap.risk_factors.append(rf)
            existing_links = {
                (link.source, link.target, link.relation)
                for link in snap.temporal_links
            }
            for link in observation.temporal_links:
                key = (link.source, link.target, link.relation)
                if key not in existing_links:
                    snap.temporal_links.append(link)
                    existing_links.add(key)
            # Promote pertinent negatives. If a denied symptom is later
            # affirmed (its canonical_name appears in observation.symptoms),
            # drop it from the denial list so the matrix stays coherent.
            affirmed_now = {s.canonical_name for s in observation.symptoms}
            for denied in observation.denied_symptoms:
                if denied in affirmed_now:
                    continue
                if denied not in snap.denied_symptoms:
                    snap.denied_symptoms.append(denied)
            if affirmed_now:
                snap.denied_symptoms = [
                    d for d in snap.denied_symptoms if d not in affirmed_now
                ]

    def snapshot(self, session_id: str) -> SymptomGraphSnapshot:
        with self._lock:
            return self._ensure(session_id)

    def enrich_recent_symptom(
        self,
        session_id: str,
        *,
        onset=None,
        severity_nrs: int | None = None,
        body_site: str | None = None,
        character: list[str] | None = None,
    ) -> bool:
        """Patch the most recently added symptom with slot fillers from a
        follow-up turn that did not introduce a new symptom name.

        Returns ``True`` when at least one slot was filled.
        """
        with self._lock:
            snap = self._ensure(session_id)
            if not snap.symptoms:
                return False
            last = snap.symptoms[-1]
            updated = False
            patch: dict = {}
            if onset is not None and last.onset is None:
                patch["onset"] = onset
                updated = True
            if severity_nrs is not None and last.severity_nrs is None:
                patch["severity_nrs"] = severity_nrs
                updated = True
            if body_site is not None and not last.body_site:
                patch["body_site"] = body_site
                updated = True
            if character:
                merged = list(dict.fromkeys([*last.character, *character]))
                if merged != last.character:
                    patch["character"] = merged
                    updated = True
            if updated:
                snap.symptoms[-1] = last.model_copy(update=patch)
            return updated

    def record_question(
        self, session_id: str, question: str, *, max_history: int = 8
    ) -> None:
        """Append the agent's question to the per-session log (capped FIFO)."""
        with self._lock:
            snap = self._ensure(session_id)
            snap.asked_questions.append(question.strip())
            if len(snap.asked_questions) > max_history:
                snap.asked_questions = snap.asked_questions[-max_history:]

    def record_patient_turn(
        self, session_id: str, utterance: str, *, max_history: int = 8
    ) -> None:
        """Append the patient's reply to the per-session log (capped FIFO)."""
        with self._lock:
            snap = self._ensure(session_id)
            snap.patient_turns.append(utterance.strip())
            if len(snap.patient_turns) > max_history:
                snap.patient_turns = snap.patient_turns[-max_history:]

    def recent_dialogue(
        self, session_id: str, *, last_n: int = 5
    ) -> list[tuple[str, str]]:
        """Return interleaved ``(role, text)`` for the last ``n`` exchanges."""
        with self._lock:
            snap = self._ensure(session_id)
            qs = snap.asked_questions[-last_n:]
            ps = snap.patient_turns[-last_n:]
            out: list[tuple[str, str]] = []
            for i in range(max(len(qs), len(ps))):
                if i < len(qs):
                    out.append(("agent", qs[i]))
                if i < len(ps):
                    out.append(("patient", ps[i]))
            return out

    def set_last_target_slot(self, session_id: str, slot: str | None) -> None:
        """Track which slot the agent is currently probing."""
        with self._lock:
            snap = self._ensure(session_id)
            snap.last_target_slot = slot

    def record_discriminator(
        self,
        session_id: str,
        *,
        key: str,
        question: str,
        condition: str,
    ) -> None:
        """Mark a discriminator probe as asked. Idempotent."""
        with self._lock:
            snap = self._ensure(session_id)
            if key in snap.discriminators_asked:
                return
            snap.discriminators_asked.add(key)
            snap.discriminator_answers.append(
                {
                    "key": key,
                    "question": question,
                    "condition": condition,
                    "answer": "",
                }
            )

    def attach_discriminator_answer(
        self, session_id: str, key: str, answer: str
    ) -> None:
        """Fill the answer for a previously-asked discriminator probe."""
        with self._lock:
            snap = self._ensure(session_id)
            for entry in snap.discriminator_answers:
                if entry["key"] == key and not entry["answer"]:
                    entry["answer"] = answer.strip()
                    break

    def satisfy_slot(self, session_id: str, slot: str) -> None:
        """Mark ``slot`` as satisfied by the patient (denial or explicit answer)."""
        with self._lock:
            snap = self._ensure(session_id)
            snap.satisfied_slots.add(slot)

    def record_allergies(self, session_id: str, items: list[str]) -> None:
        """Append unique allergy entries to the session."""
        if not items:
            return
        with self._lock:
            snap = self._ensure(session_id)
            for a in items:
                if a and a not in snap.allergies:
                    snap.allergies.append(a)

    def record_risk_factors(self, session_id: str, items: list[str]) -> None:
        """Append unique risk-factor entries (used for denial-as-data)."""
        if not items:
            return
        with self._lock:
            snap = self._ensure(session_id)
            for r in items:
                if r and r not in snap.risk_factors:
                    snap.risk_factors.append(r)

    def record_medications(self, session_id: str, items: list[str]) -> None:
        """Append unique medication entries."""
        if not items:
            return
        with self._lock:
            snap = self._ensure(session_id)
            for m in items:
                if m and m not in snap.medications:
                    snap.medications.append(m)

    def bump_slot_ask(self, session_id: str, slot: str, *, max_asks: int = 2) -> None:
        """Increment the ask counter for ``slot`` and skip it past the budget.

        Stops the agent from re-asking the same question when the patient
        cannot or does not want to provide that slot, advancing the
        interview to the next gap instead of looping.
        """
        with self._lock:
            snap = self._ensure(session_id)
            snap.slot_ask_count[slot] = snap.slot_ask_count.get(slot, 0) + 1
            if snap.slot_ask_count[slot] >= max_asks:
                snap.skipped_slots.add(slot)

    def find_unfilled_slots(self, session_id: str) -> list[str]:
        """Return the canonical slots that still need data for ``session_id``.

        The heuristic is intentionally simple: a slot is considered filled if
        any of its observable evidence is present on at least one symptom. This
        keeps the agent loop deterministic and avoids LLM-driven slot tracking.
        """
        with self._lock:
            snap = self._ensure(session_id)
            unfilled: list[str] = []
            symptoms = snap.symptoms
            has_symptom = bool(symptoms)

            def _filled(predicate) -> bool:
                return any(predicate(s) for s in symptoms)

            # The pain-shaped OPQRST slots (location, radiation, character,
            # severity-NRS) only apply to localizable complaints. When no
            # symptom is localizable (apnea, insonnia, febbre, astenia…) those
            # slots are skipped so the deterministic fallback never asks
            # "where do you feel your sleep apnea?" or "how strong is the
            # pain?" for a non-pain complaint. The reasoner path handles this
            # natively; this keeps the LLM-down fallback sane too.
            localizable_present = _filled(
                lambda s: _is_localizable(s.canonical_name, s.raw_quote)
            )

            checks = {
                "chief_complaint": has_symptom,
                "onset": _filled(lambda s: s.onset is not None),
                "location": (not localizable_present)
                or _filled(lambda s: bool(s.body_site)),
                "character": (not localizable_present)
                or _filled(lambda s: bool(s.character)),
                "radiation": (not localizable_present)
                or _filled(lambda s: any("radia" in c.lower() for c in s.character)),
                "severity": (not localizable_present)
                or _filled(lambda s: s.severity_nrs is not None),
                "timing": _filled(lambda s: s.onset is not None),
                "modifiers": _filled(
                    lambda s: any(
                        c.lower().startswith(("peggiora", "migliora"))
                        for c in s.character
                    )
                ),
                "associated_symptoms": len(symptoms) >= 2,
                "past_medical_history": bool(snap.risk_factors),
                "allergies": bool(snap.allergies),
                "medications": bool(snap.medications),
            }
            for slot in ANAMNESIS_SLOTS:
                if slot in snap.skipped_slots:
                    continue
                # An explicit "no/nessuno/niente" reply marks the slot as
                # satisfied even if the underlying evidence list is empty.
                if slot in snap.satisfied_slots:
                    continue
                if not checks.get(slot, False):
                    unfilled.append(slot)
            return unfilled

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
