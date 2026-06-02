"""
Domain-specific Ollama provider for MedGemma (or compatible medical LLM).

Wraps :class:`core.services.llm.providers.ollama_provider.OllamaProvider`
with two upgrades over the base provider:

    * **Schema-constrained generation** — passes the Pydantic JSON schema
      to Ollama via ``format=<json_schema>`` (Ollama >= 0.5). The model is
      constrained at decode time to emit a token sequence that satisfies
      the schema, eliminating the "wrong key name" drift that small medical
      models exhibit when only ``format=json`` is requested.
    * **Schema-in-prompt fallback + structural repair** — the prompt also
      embeds the schema and an example, and parsed payloads go through a
      best-effort coercion pass (singular→list, str→Symptom object) before
      strict Pydantic validation. Two retries on residual mismatch.

Patient data never leaves the host because the underlying Ollama server
runs locally.
"""

from __future__ import annotations

import json
from typing import Any, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from core.observability.logging import get_logger
from core.services.llm.providers.ollama_provider import OllamaProvider

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class StructuredOutputError(RuntimeError):
    """Raised when the LLM fails to produce a schema-valid payload."""


class OllamaMedGemmaProvider(OllamaProvider):
    """Local MedGemma provider with strict JSON-mode generation."""

    def __init__(
        self,
        *,
        api_base: str | None = None,
        model_id: str = "medgemma:4b",
        temperature: float = 0.2,
        context_window: int = 8192,
        keep_alive: str = "30m",
        num_predict: int | None = None,
    ) -> None:
        super().__init__(api_base=api_base)
        self.model_id = model_id
        self.temperature = temperature
        self.context_window = context_window
        # ``keep_alive`` keeps the model resident in the Ollama server
        # between turns so each interview turn does not pay the cold-load
        # penalty (~8s for a 27B model). ``num_predict`` optionally caps the
        # generated token count to bound latency on large models.
        self.keep_alive = keep_alive
        self.num_predict = num_predict

    def _options(self) -> dict[str, Any]:
        opts: dict[str, Any] = {
            "temperature": self.temperature,
            "num_ctx": self.context_window,
        }
        if self.num_predict is not None:
            opts["num_predict"] = self.num_predict
        return opts

    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
    ) -> str:
        """Free-form generation."""
        client = self._ensure_client()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = await client.chat(
            model=self.model_id,
            messages=messages,
            keep_alive=self.keep_alive,
            options=self._options(),
        )
        return self._response_content(response)

    async def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
        max_retries: int = 2,
    ) -> T:
        """Generate JSON output validated against ``schema``.

        Uses Ollama's schema-constrained ``format=<json_schema>`` mode and
        injects the schema + a tiny example into the prompt as a belt-and-
        braces safeguard. Parsed payloads go through a structural repair
        pass before strict validation.
        """
        client = self._ensure_client()
        schema_dict = schema.model_json_schema()
        schema_str = json.dumps(schema_dict, ensure_ascii=False)

        base_messages: list[dict[str, str]] = []
        if system:
            base_messages.append({"role": "system", "content": system})

        last_error: str | None = None
        attempt = 0
        while attempt <= max_retries:
            user_content = self._build_user_prompt(
                prompt=prompt,
                schema_str=schema_str,
                last_error=last_error,
            )
            messages = [*base_messages, {"role": "user", "content": user_content}]
            try:
                response = await client.chat(
                    model=self.model_id,
                    messages=messages,
                    format=schema_dict,
                    keep_alive=self.keep_alive,
                    options=self._options(),
                )
            except Exception as exc:  # noqa: BLE001
                last_error = f"ollama transport: {exc}"[:300]
                logger.warning(
                    "MedGemma structured output transport retry %d: %s",
                    attempt,
                    last_error,
                )
                attempt += 1
                continue

            text = self._response_content(response)
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                last_error = f"json parse: {exc}"[:300]
                logger.warning(
                    "MedGemma structured output parse retry %d: %s",
                    attempt,
                    last_error,
                )
                attempt += 1
                continue

            repaired = self._coerce_payload(payload, schema)
            try:
                return schema.model_validate(repaired)
            except ValidationError as exc:
                last_error = str(exc)[:300]
                logger.warning(
                    "MedGemma structured output validate retry %d: %s",
                    attempt,
                    last_error,
                )
                attempt += 1

        raise StructuredOutputError(
            f"MedGemma failed to produce a schema-valid payload after "
            f"{max_retries + 1} attempts. Last error: {last_error}"
        )

    @staticmethod
    def _build_user_prompt(
        *,
        prompt: str,
        schema_str: str,
        last_error: str | None,
    ) -> str:
        retry_hint = (
            ""
            if last_error is None
            else f"\n\nL'ultimo tentativo era invalido: {last_error}. Correggi."
        )
        return (
            f"{prompt}\n\n"
            "Restituisci esclusivamente JSON conforme a questo schema "
            "(non aggiungere chiavi extra, usa esattamente i nomi indicati):\n"
            f"{schema_str}"
            f"{retry_hint}"
        )

    @staticmethod
    def _response_content(response: Any) -> str:
        if isinstance(response, dict):
            message = response.get("message") or {}
            content = message.get("content")
            if isinstance(content, str):
                return content
        message = getattr(response, "message", None)
        if message is not None:
            content = getattr(message, "content", None)
            if isinstance(content, str):
                return content
        return str(response)

    @staticmethod
    def _coerce_payload(payload: Any, schema: type[BaseModel]) -> Any:
        """Best-effort structural repair for common MedGemma drifts.

        Handles only the ``ExtractedObservation`` and ``DifferentialDiagnosis``
        shapes used by BaselithMed; everything else passes through unchanged.
        """
        if not isinstance(payload, dict):
            return payload

        schema_name = schema.__name__
        if schema_name == "ExtractedObservation":
            return _repair_extracted_observation(payload)
        if schema_name == "DifferentialDiagnosis":
            return _repair_differential_diagnosis(payload)
        return payload


def _repair_extracted_observation(payload: dict[str, Any]) -> dict[str, Any]:
    repaired: dict[str, Any] = {
        "symptoms": [],
        "body_sites": [],
        "medications": [],
        "risk_factors": [],
        "temporal_links": [],
    }

    raw_symptoms: list[Any] = []
    for key in ("symptoms", "symptom", "observations"):
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            raw_symptoms.extend(value)
        else:
            raw_symptoms.append(value)

    for item in raw_symptoms:
        if isinstance(item, str):
            repaired["symptoms"].append(
                {
                    "canonical_name": item,
                    "raw_quote": item,
                    "source_turn_id": str(uuid4()),
                }
            )
        elif isinstance(item, dict):
            d = dict(item)
            if "name" in d and "canonical_name" not in d:
                d["canonical_name"] = d.pop("name")
            d.setdefault("canonical_name", "unknown")
            d.setdefault("raw_quote", d.get("canonical_name", ""))
            d.setdefault("source_turn_id", str(uuid4()))
            if "severity" in d and "severity_nrs" not in d:
                try:
                    d["severity_nrs"] = int(d.pop("severity"))
                except (TypeError, ValueError):
                    d.pop("severity", None)
            if "site" in d and "body_site" not in d:
                d["body_site"] = d.pop("site")
            character = d.get("character")
            if isinstance(character, str):
                d["character"] = [character] if character else []
            repaired["symptoms"].append(d)

    for src, dest in (
        ("body_sites", "body_sites"),
        ("body_site", "body_sites"),
        ("sites", "body_sites"),
        ("medications", "medications"),
        ("drugs", "medications"),
        ("risk_factors", "risk_factors"),
        ("risks", "risk_factors"),
        ("temporal_links", "temporal_links"),
        ("timeline", "temporal_links"),
    ):
        value = payload.get(src)
        if value is None:
            continue
        if isinstance(value, list):
            repaired[dest].extend(value)
        else:
            repaired[dest].append(value)

    repaired["body_sites"] = [str(x) for x in repaired["body_sites"] if x]
    repaired["medications"] = [str(x) for x in repaired["medications"] if x]
    repaired["risk_factors"] = [str(x) for x in repaired["risk_factors"] if x]
    return repaired


def _repair_differential_diagnosis(payload: dict[str, Any]) -> dict[str, Any]:
    repaired: dict[str, Any] = {
        "hypotheses": [],
        "model_id": payload.get("model_id") or payload.get("model") or "medgemma",
        "notes": payload.get("notes"),
    }
    raw = payload.get("hypotheses") or payload.get("diagnoses") or []
    if isinstance(raw, dict):
        raw = [raw]
    for item in raw:
        if not isinstance(item, dict):
            continue
        d = dict(item)
        if "name" in d and "condition" not in d:
            d["condition"] = d.pop("name")
        d.setdefault("condition", "unknown")
        if "confidence" in d:
            try:
                conf = float(d["confidence"])
                if conf > 1.0:
                    conf = conf / 100.0
                d["confidence"] = max(0.0, min(1.0, conf))
            except (TypeError, ValueError):
                d["confidence"] = 0.0
        else:
            d["confidence"] = 0.0
        for list_key in (
            "supporting_findings",
            "contradicting_findings",
            "recommended_workup",
        ):
            value = d.get(list_key)
            if value is None:
                d[list_key] = []
            elif isinstance(value, str):
                d[list_key] = [value]
            elif not isinstance(value, list):
                d[list_key] = [str(value)]
        repaired["hypotheses"].append(d)
    return repaired
