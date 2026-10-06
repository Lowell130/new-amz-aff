"""Interfaccia LLM astratta (usata dall'AI Advisor nella Fase 8).

Il dominio applicativo dipende solo da LLMProvider: cambiare OpenAI/Gemini/altro
non deve richiedere modifiche al resto del codice.
Regola: l'LLM NON è mai la fonte dei dati prodotto; riceve solo dati strutturati
già selezionati dal motore di scoring e li spiega.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel


class LLMError(RuntimeError):
    pass


class LLMMessage(BaseModel):
    role: str  # system | user | assistant
    content: str


class LLMProvider(Protocol):
    name: str

    async def complete(self, messages: list[LLMMessage], *, json_schema: dict[str, Any] | None = None) -> str: ...


class NullLLMProvider:
    """Provider di default quando nessun LLM è configurato."""

    name = "none"

    async def complete(self, messages: list[LLMMessage], *, json_schema: dict[str, Any] | None = None) -> str:
        raise LLMError("Nessun LLM configurato (LLM_PROVIDER=none)")


def parse_json(text: str) -> dict[str, Any]:
    """Estrae un oggetto JSON anche se il modello lo avvolge in ```json ... ```."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("{"):]
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end < start:
        raise LLMError("Risposta LLM non in formato JSON")
    try:
        data = json.loads(t[start : end + 1])
    except json.JSONDecodeError as e:
        raise LLMError("JSON LLM non valido") from e
    if not isinstance(data, dict):
        raise LLMError("JSON LLM non è un oggetto")
    return data
