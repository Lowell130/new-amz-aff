"""Provider LLM reali (OpenAI, Google Gemini) via HTTP, senza SDK.

Nota: il nome del modello va SEMPRE indicato in LLM_MODEL (i nomi cambiano spesso:
controllare la documentazione ufficiale del provider). Nessuna chiave nel codice.

Nei log NON finisce mai il contenuto dei messaggi: solo provider, modello, durata, esito.
"""

from __future__ import annotations

import copy
import logging
import time
from typing import Any

import httpx

from app.ai.base import LLMError, LLMMessage

log = logging.getLogger("app.llm")

TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class _BaseHTTPProvider:
    name = "base"

    def __init__(self, api_key: str, model: str):
        if not api_key or not model:
            raise LLMError(f"{self.name}: LLM_API_KEY e LLM_MODEL sono obbligatori")
        self.api_key = api_key
        self.model = model

    def _log(self, started: float, ok: bool, extra: str = "") -> None:
        log.info("llm_call provider=%s model=%s ms=%d ok=%s %s",
                 self.name, self.model, int((time.monotonic() - started) * 1000), ok, extra)


class OpenAIProvider(_BaseHTTPProvider):
    """Chat Completions API con output strutturato (response_format=json_schema)."""

    name = "openai"
    url = "https://api.openai.com/v1/chat/completions"

    async def complete(self, messages: list[LLMMessage], *, json_schema: dict[str, Any] | None = None) -> str:
        body: dict[str, Any] = {"model": self.model, "messages": [m.model_dump() for m in messages]}
        if json_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "advisor_output", "schema": json_schema, "strict": True},
            }
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                r = await client.post(self.url, json=body, headers={"Authorization": f"Bearer {self.api_key}"})
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            self._log(started, False, type(e).__name__)
            raise LLMError(f"OpenAI: {type(e).__name__}") from e
        self._log(started, True)
        return content or ""


def to_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Converte il sottoinsieme di JSON Schema che usiamo nel formato OpenAPI di Gemini."""
    s = copy.deepcopy(schema)
    out: dict[str, Any] = {}
    t = s.get("type")
    if isinstance(t, list):
        non_null = [x for x in t if x != "null"]
        if len(non_null) != len(t):
            out["nullable"] = True
        t = non_null[0] if non_null else "string"
    if t:
        out["type"] = str(t).upper()
    if "enum" in s:
        out["enum"] = [v for v in s["enum"] if v is not None]
    if "items" in s:
        out["items"] = to_gemini_schema(s["items"])
    if "properties" in s:
        out["properties"] = {k: to_gemini_schema(v) for k, v in s["properties"].items()}
    if "required" in s:
        out["required"] = list(s["required"])
    return out


class GeminiProvider(_BaseHTTPProvider):
    """Gemini API generateContent con responseSchema."""

    name = "gemini"

    async def complete(self, messages: list[LLMMessage], *, json_schema: dict[str, Any] | None = None) -> str:
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        contents = [
            {"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.content}]}
            for m in messages
            if m.role != "system"
        ]
        body: dict[str, Any] = {"contents": contents}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if json_schema is not None:
            body["generationConfig"] = {
                "responseMimeType": "application/json",
                "responseSchema": to_gemini_schema(json_schema),
            }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                r = await client.post(url, json=body, headers={"x-goog-api-key": self.api_key})
            r.raise_for_status()
            parts = r.json()["candidates"][0]["content"]["parts"]
            content = "".join(p.get("text", "") for p in parts)
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            self._log(started, False, type(e).__name__)
            raise LLMError(f"Gemini: {type(e).__name__}") from e
        self._log(started, True)
        return content
