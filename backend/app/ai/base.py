"""Interfaccia LLM astratta (usata dall'AI Advisor nella Fase 8).

Il dominio applicativo dipende solo da LLMProvider: cambiare OpenAI/Gemini/altro
non deve richiedere modifiche al resto del codice.
Regola: l'LLM NON è mai la fonte dei dati prodotto; riceve solo dati strutturati
già selezionati dal motore di scoring e li spiega.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel


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
        raise RuntimeError("Nessun LLM configurato (LLM_PROVIDER=none)")
