"""Local OpenAI-compatible mock for offline dev. No real inference.

Returns canned JSON responses matching agent prompt schemas.
Run: uv run python scripts/mock_llm.py  (binds 127.0.0.1:8000)
"""

from __future__ import annotations
import json
import re
import time
import uuid
from typing import Any
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn


app = FastAPI(title="doCheck Mock LLM")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.1
    max_tokens: int = 2048
    response_format: dict[str, Any] | None = None


def _detect_agent(messages: list[ChatMessage]) -> str:
    text = " ".join(m.content for m in messages).lower()
    if "structure extractor" in text:
        return "structurer"
    if "legal compliance auditor" in text:
        return "legal"
    if "pii verification" in text:
        return "pii"
    if "report synthesizer" in text:
        return "synthesizer"
    return "unknown"


def _structurer_response() -> dict:
    return {
        "structure": [
            {
                "id": "s1",
                "type": "title",
                "label": "Documento",
                "parent_id": None,
                "page": 1,
                "line_start": 1,
                "line_end": 1,
                "chunk_ids": [],
            },
        ]
    }


def _legal_response(messages: list[ChatMessage]) -> dict:
    text = " ".join(m.content for m in messages)
    chunk_ids = re.findall(r"'id': '(c-[a-f0-9]+)'", text)
    if not chunk_ids:
        return {"findings": []}
    return {
        "findings": [
            {
                "rule_id": "GDPR-Art-13",
                "policy_id": "IT_GDPR_2026",
                "policy_version": "3.0.0",
                "severity": "FAIL",
                "chunk_id": chunk_ids[0],
                "line_start": 1,
                "line_end": 5,
                "policy_excerpt": "Il titolare informa l'interessato del periodo di conservazione dei dati personali.",
                "explanation": "[MOCK] Manca clausola retention dati.",
                "suggestion": "Aggiungere clausola conservazione dati con periodo specifico.",
                "confidence": 0.92,
                "reasoning": [
                    {
                        "action": "retrieve_policy",
                        "input": {"query": "retention"},
                        "output": {"rule_ids": ["GDPR-Art-13"]},
                    },
                    {"thought": "[MOCK] chunk lacks retention clause"},
                ],
            }
        ]
    }


def _pii_response() -> dict:
    return {"verified": [], "rejected": []}


def _synth_response() -> dict:
    return {
        "score": 78,
        "summary": "[MOCK] Analisi mock.",
        "by_severity": {"FAIL": 1, "WARN": 0, "PASS": 0},
        "top_risks": [],
    }


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    agent = _detect_agent(req.messages)
    payload: dict
    match agent:
        case "structurer":
            payload = _structurer_response()
        case "legal":
            payload = _legal_response(req.messages)
        case "pii":
            payload = _pii_response()
        case "synthesizer":
            payload = _synth_response()
        case _:
            payload = {}

    content = json.dumps(payload)
    return {
        "id": f"mock-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@app.get("/health")
async def health():
    return {"status": "ok", "mock": True}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
