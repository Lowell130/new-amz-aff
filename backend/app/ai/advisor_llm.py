"""Uso dell'LLM nell'AI Advisor: SOLO due compiti, entrambi con paracadute deterministico.

1. extract(): trasforma il messaggio in risposte strutturate alle domande dei Finder/Configuratori
   esistenti (lo schema JSON è generato dalle domande stesse). Se l'LLM non è configurato o
   risponde male -> estrattore a regole (parole chiave editoriali + regex per il budget).
2. explain(): spiega una raccomandazione GIÀ calcolata dai motori deterministici, usando solo i
   dati passati. Il testo viene verificato: se cita prezzi che non sono nei dati -> si usa il
   testo a modello (template). L'LLM non sceglie mai i prodotti.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.ai.base import LLMError, LLMMessage, LLMProvider, NullLLMProvider, parse_json
from app.models.finder import FinderQuestion

log = logging.getLogger(__name__)


@dataclass
class Target:
    key: str  # "finder:scarpe-trekking" | "configurator:kit-trekking"
    kind: Literal["finder", "configurator"]
    slug: str
    title: str
    description: str
    questions: list[FinderQuestion]
    keywords: list[str]
    key_questions: list[str]


class Extraction(BaseModel):
    target: str | None = None
    off_topic: bool = False
    answers: dict[str, Any] = Field(default_factory=dict)
    source: Literal["llm", "rules"] = "rules"


# --------------------------------------------------------------------- utilità testo
def norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in t if not unicodedata.combining(c)).replace("’", "'")


def _find(text: str, kw: str) -> int | None:
    m = re.search(r"(?<![a-z0-9])" + re.escape(norm(kw)), text)
    return m.start() if m else None


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", ".")) if re.search(r"\.\d{3}\b", s) else float(s.replace(",", "."))


BUDGET_PATTERNS = [
    r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?\s*(?:€|euro|eur\b)",
    r"€\s*(\d{1,3}(?:\.\d{3})+|\d+)",
    r"(?:budget|spendere|spesa|massimo|max|fino a|entro)\D{0,15}?(\d{2,5})",
]


def find_budget(text: str) -> float | None:
    t = norm(text)
    for p in BUDGET_PATTERNS:
        m = re.search(p, t)
        if m:
            return _num(m.group(1))
    return None


def all_questions(targets: list[Target]) -> dict[str, FinderQuestion]:
    out: dict[str, FinderQuestion] = {}
    for t in targets:
        for q in t.questions:
            out.setdefault(q.id, q)
    return out


# ------------------------------------------------------------------- estrattore a regole
def extract_rules(text: str, targets: list[Target], pending: FinderQuestion | None = None) -> Extraction:
    t = norm(text)
    # destinazione: lo strumento con più parole chiave trovate
    scores = {tg.key: sum(1 for kw in tg.keywords if _find(t, kw) is not None) for tg in targets}
    best = max(scores.values(), default=0)
    winners = [k for k, v in scores.items() if v == best]
    target = winners[0] if best > 0 and len(winners) == 1 else None

    answers: dict[str, Any] = {}
    for q in all_questions(targets).values():
        if q.type == "single_choice":
            hits = []
            for o in q.options:
                kws = list(o.keywords)
                if pending is not None and pending.id == q.id:
                    kws.append(o.label)  # alla domanda in sospeso si può rispondere con l'etichetta
                for kw in kws:
                    pos = _find(t, kw)
                    if pos is not None:
                        hits.append((-len(kw), pos, o.value))
            if hits:
                answers[q.id] = sorted(hits)[0][2]
        elif q.type == "multiple_choice":
            found = []
            for o in q.options:
                kws = list(o.keywords) + ([o.label] if pending is not None and pending.id == q.id else [])
                pos = min((p for p in (_find(t, kw) for kw in kws) if p is not None), default=None)
                if pos is not None:
                    found.append((pos, o.value))
            if found:
                answers[q.id] = [v for _, v in sorted(found)][: q.max_choices or None]
        elif q.type == "boolean":
            if any(_find(t, kw) is not None for kw in q.keywords_true):
                answers[q.id] = True
            elif pending is not None and pending.id == q.id:
                if re.match(r"^\s*(si|certo|esatto)\b", t):
                    answers[q.id] = True
                elif re.match(r"^\s*no\b", t):
                    answers[q.id] = False
        elif q.type in ("range", "number"):
            value = find_budget(text) if q.maps_to == "budget_max" else None
            if value is None and pending is not None and pending.id == q.id:
                m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)", t)
                value = _num(m.group(1)) if m else None
            if value is not None:
                answers[q.id] = value

    return Extraction(target=target, off_topic=target is None and not answers, answers=answers, source="rules")


# ------------------------------------------------------------------ schema per l'LLM
def extraction_schema(targets: list[Target]) -> dict[str, Any]:
    props: dict[str, Any] = {}
    for q in all_questions(targets).values():
        values = sorted({o.value for tg in targets for qq in tg.questions if qq.id == q.id for o in qq.options})
        if q.type == "single_choice":
            props[q.id] = {"type": ["string", "null"], "enum": [*values, None]}
        elif q.type == "multiple_choice":
            props[q.id] = {"type": ["array", "null"], "items": {"type": "string", "enum": values}}
        elif q.type in ("range", "number"):
            props[q.id] = {"type": ["number", "null"]}
        elif q.type == "boolean":
            props[q.id] = {"type": ["boolean", "null"]}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["target", "off_topic", "answers"],
        "properties": {
            "target": {"type": ["string", "null"], "enum": [*(t.key for t in targets), None]},
            "off_topic": {"type": "boolean"},
            "answers": {"type": "object", "additionalProperties": False, "required": list(props), "properties": props},
        },
    }


def _extraction_prompt(targets: list[Target], known: dict[str, Any], pending: FinderQuestion | None) -> str:
    lines = [
        "Sei il modulo di comprensione di un consulente d'acquisto italiano.",
        "Dal messaggio dell'utente compila un JSON con le risposte alle domande elencate.",
        "REGOLE: compila un campo SOLO se l'utente lo dice o lo implica chiaramente, altrimenti null.",
        "Non inventare budget, esperienza o preferenze. Il budget è un numero in euro.",
        "target = lo strumento più adatto alla richiesta (null se non è chiaro).",
        "off_topic = true se la richiesta non riguarda nessuno degli strumenti.",
        "",
        "STRUMENTI:",
    ]
    lines += [f"- {t.key}: {t.title} — {t.description}" for t in targets]
    lines += ["", "DOMANDE (id: testo | valori ammessi):"]
    for q in all_questions(targets).values():
        if q.options:
            opts = ", ".join(f"{o.value}={o.label}" for o in q.options)
        else:
            opts = q.type + (f" {q.min}-{q.max} {q.unit or ''}" if q.min is not None else "")
        lines.append(f"- {q.id}: {q.question} | {opts}")
    if known:
        lines += ["", f"Già noto (non serve ripeterlo, ma aggiornalo se l'utente cambia idea): {json.dumps(known, ensure_ascii=False)}"]
    if pending:
        lines += ["", f"L'ultima domanda fatta all'utente era: {pending.id} ({pending.question})."]
    return "\n".join(lines)


# ------------------------------------------------------------------- spiegazione
PRICE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?\s*(?:€|euro)")


def _numbers_in(obj: Any) -> set[float]:
    out: set[float] = set()
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.add(round(float(obj), 2))
    elif isinstance(obj, str):
        for m in re.finditer(r"\d+(?:[.,]\d+)?", obj):
            try:
                out.add(round(_num(m.group(0)), 2))
            except ValueError:
                pass
    elif isinstance(obj, dict):
        for v in obj.values():
            out |= _numbers_in(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _numbers_in(v)
    return out


def grounded(text: str, payload: dict[str, Any]) -> bool:
    """Ogni importo in euro citato nel testo deve esistere nei dati passati (tolleranza 1 €)."""
    allowed = _numbers_in(payload)
    for m in PRICE_RE.finditer(text):
        val = _num(m.group(1)) + (float(f"0.{m.group(2)}") if m.group(2) else 0)
        if not any(abs(val - a) <= 1.0 for a in allowed):
            return False
    return True


def _eur(x: float) -> str:
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s.removesuffix(",00") + " €"


def template_explanation(payload: dict[str, Any]) -> str:
    p = payload["profilo"]
    uso = ", ".join(p.get("uso") or []) or "le tue uscite"
    budget = payload.get("budget")
    head = f"Per {uso.lower()}" + (f" con un budget fino a {_eur(budget)}" if budget else "")
    if payload["tipo"] == "kit":
        parts = []
        for it in payload["prodotti"]:
            price = f" ({_eur(it['prezzo_attuale'])})" if it.get("prezzo_attuale") is not None else ""
            parts.append(f"{it['ruolo'].lower()}: {it['nome']} di {it['marca']}{price}")
        txt = f"{head} ti propongo questo kit — " + "; ".join(parts) + "."
        if payload.get("totale_prezzi_aggiornati"):
            txt += f" Totale con i prezzi aggiornati: {_eur(payload['totale_prezzi_aggiornati'])}."
        if payload.get("esclusi"):
            txt += " Non ho incluso: " + ", ".join(x.lower() for x in payload["esclusi"]) + "."
        return txt
    prods = payload["prodotti"]
    if not prods:
        return f"{head} non ho trovato prodotti che rispettino tutti i requisiti. Prova ad alzare il budget o a togliere qualche vincolo."
    best = prods[0]
    motivi = "; ".join(m[0].lower() + m[1:] for m in best.get("motivi", [])[:3])
    txt = f"{head} la scelta più adatta è {best['nome']} di {best['marca']}" + (f": {motivi}." if motivi else ".")
    for alt in prods[1:3]:
        txt += f" {alt['ruolo']}: {alt['nome']} di {alt['marca']}."
    return txt


EXPLAIN_SYSTEM = (
    "Sei un consulente d'acquisto italiano, chiaro e concreto. Spiega in massimo 90 parole perché "
    "i prodotti indicati sono adatti al profilo. USA SOLO i dati forniti nel JSON: non inventare "
    "caratteristiche, prezzi, recensioni o disponibilità. Cita un prezzo solo se presente in "
    "'prezzo_attuale' o nei totali. Non usare elenchi puntati né markdown. Non consigliare altri prodotti."
)


class AdvisorLLM:
    def __init__(self, provider: LLMProvider | None = None):
        self.provider = provider or NullLLMProvider()

    @property
    def enabled(self) -> bool:
        return not isinstance(self.provider, NullLLMProvider)

    async def extract(
        self, text: str, targets: list[Target], known: dict[str, Any], pending: FinderQuestion | None
    ) -> Extraction:
        rules = extract_rules(text, targets, pending)
        if not self.enabled:
            return rules
        try:
            raw = await self.provider.complete(
                [
                    LLMMessage(role="system", content=_extraction_prompt(targets, known, pending)),
                    LLMMessage(role="user", content=text),
                ],
                json_schema=extraction_schema(targets),
            )
            data = parse_json(raw)
            ex = Extraction.model_validate({**data, "source": "llm"})
        except (LLMError, ValidationError) as e:
            log.warning("Estrazione LLM fallita (%s): uso le regole", type(e).__name__)
            return rules
        keys = {t.key for t in targets}
        qids = set(all_questions(targets))
        answers = {k: v for k, v in (ex.answers or {}).items() if k in qids and v not in (None, [])}
        target = ex.target if ex.target in keys else None
        return Extraction(target=target, off_topic=ex.off_topic, answers=answers, source="llm")

    async def explain(self, payload: dict[str, Any]) -> tuple[str, str]:
        """Restituisce (testo, origine). Origine: "llm" oppure "template"."""
        fallback = template_explanation(payload)
        if not self.enabled:
            return fallback, "template"
        try:
            text = await self.provider.complete([
                LLMMessage(role="system", content=EXPLAIN_SYSTEM),
                LLMMessage(role="user", content=json.dumps(payload, ensure_ascii=False)),
            ])
        except LLMError as e:
            log.warning("Spiegazione LLM fallita (%s): uso il modello di testo", type(e).__name__)
            return fallback, "template"
        text = (text or "").strip()
        if not text or len(text) > 1500 or not grounded(text, payload):
            log.warning("Spiegazione LLM scartata (vuota, troppo lunga o con prezzi non presenti nei dati)")
            return fallback, "template"
        return text, "llm"
