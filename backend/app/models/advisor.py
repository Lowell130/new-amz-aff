"""Sessione dell'AI Advisor.

Privacy: NON salviamo il testo dei messaggi dell'utente. Conserviamo solo lo stato
strutturato utile alla raccomandazione (strumento scelto, risposte, domanda in sospeso).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AdvisorState(BaseModel):
    target: str | None = None  # "finder:<slug>" | "configurator:<slug>"
    answers: dict[str, Any] = Field(default_factory=dict)
    pending_question: str | None = None
    asked: list[str] = Field(default_factory=list)


class AdvisorSession(BaseModel):
    session_id: str
    created_at: datetime
    updated_at: datetime
    turns: int = 0
    state: AdvisorState = Field(default_factory=AdvisorState)
    last_finder_session: str | None = None
    last_config_session: str | None = None
