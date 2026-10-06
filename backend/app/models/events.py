"""Eventi di tracking. Nessun dato personale: solo tipo, sessione anonima e pochi campi ammessi."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "finder_started",
    "finder_question_viewed",
    "finder_answered",
    "finder_completed",
    "recommendation_viewed",
    "affiliate_link_clicked",
    "configuration_started",
    "configuration_completed",
    "advisor_started",
    "advisor_message",
    "requirements_extracted",
    "recommendation_generated",
]

# Unici campi accettati nel payload: tutto il resto viene scartato.
ALLOWED_PAYLOAD_KEYS = {"finder_slug", "question_id", "product_id", "asin", "slot", "position", "page"}


class TrackEvent(BaseModel):
    type: EventType
    session_id: str | None = None
    payload: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    ts: datetime | None = None

    def sanitized(self) -> "TrackEvent":
        clean = {k: v for k, v in self.payload.items() if k in ALLOWED_PAYLOAD_KEYS}
        for k, v in clean.items():
            if isinstance(v, str):
                clean[k] = v[:120]
        return self.model_copy(update={"payload": clean})
