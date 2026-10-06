"""Motore di scoring: classifica i prodotti in base al PROFILO dell'utente.

Nessun "vincitore fisso": il ranking dipende interamente da budget, uso, esperienza,
priorità e vincoli. Ogni punteggio è accompagnato da motivazioni costruite solo sui
dati effettivamente disponibili (nessuna motivazione inventata).

Componenti (0..1), combinate con pesi configurabili per finder:
  budget, use_case, experience, priorities, requirements
Penalità: incompatibilità parziali (unsuitable_for).
Esclusioni: vincoli hard, prezzo oltre budget*(1+tolleranza), uso totalmente incompatibile.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from app.models.finder import (
    Explainability,
    FinderDefinition,
    PriorityRule,
    ScoringConfig,
    Requirement,
    ScoredProduct,
    UserProfile,
)
from app.models.product import ProductView

EXPERIENCE_ORDER = ["beginner", "intermediate", "expert"]
UNSUITABLE_PENALTY = 15.0
UNAVAILABLE_PENALTY = 10.0


@dataclass
class RankingOutput:
    ranked: list[ScoredProduct]
    excluded: int
    excluded_reasons: dict[str, str]


def eval_requirement(req: Requirement, attrs: dict[str, Any]) -> bool | None:
    """True/False se valutabile, None se l'attributo manca (dato sconosciuto)."""
    if req.attr not in attrs or attrs[req.attr] is None:
        return None
    v = attrs[req.attr]
    if req.op == "eq":
        return v == req.value
    if req.op == "in":
        vals = req.value if isinstance(req.value, list) else [req.value]
        if isinstance(v, list):
            return any(x in vals for x in v)
        return v in vals
    try:
        if req.op == "gte":
            return float(v) >= float(req.value)
        if req.op == "lte":
            return float(v) <= float(req.value)
    except (TypeError, ValueError):
        return None
    return None


def _fmt_eur(x: float) -> str:
    return f"{x:,.0f} €".replace(",", ".")


def _fmt_value(v: Any) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, int) and v >= 1000:
        return f"{v:,}".replace(",", ".")
    return str(v)


class ScoringEngine:
    def __init__(self, config: FinderDefinition | ScoringConfig):
        if isinstance(config, FinderDefinition):
            config = config.scoring_config()
        self.cfg = config
        self.rules: dict[str, PriorityRule] = {r.key: r for r in config.priority_rules}

    # ------------------------------------------------------------------ API
    def rank(self, profile: UserProfile, views: list[ProductView]) -> RankingOutput:
        candidates: list[ProductView] = []
        excluded: dict[str, str] = {}
        for v in views:
            why = self._exclusion_reason(profile, v)
            if why:
                excluded[v.product.id] = why
            else:
                candidates.append(v)

        ranges = self._numeric_ranges(profile, candidates)
        scored = [self._score(profile, v, ranges) for v in candidates]
        scored.sort(key=lambda s: (-s.score, s.price_for_ranking if s.price_for_ranking is not None else math.inf, s.product_id))
        return RankingOutput(ranked=scored, excluded=len(excluded), excluded_reasons=excluded)

    # ------------------------------------------------------------ esclusioni
    def _exclusion_reason(self, profile: UserProfile, v: ProductView) -> str | None:
        p = v.product
        for req in profile.requirements:
            if req.hard and eval_requirement(req, p.attributes) is not True:
                return f"vincolo obbligatorio non rispettato: {req.label}"
        price = v.ranking_price
        if profile.budget_max and price is not None:
            if price > profile.budget_max * (1 + self.cfg.budget_tolerance):
                return "fuori budget"
        if profile.use_cases and all(u in p.unsuitable_for for u in profile.use_cases):
            return "non adatto all'uso indicato"
        return None

    # ------------------------------------------------------------- scoring
    def _numeric_ranges(self, profile: UserProfile, views: list[ProductView]) -> dict[str, tuple[float, float]]:
        ranges: dict[str, tuple[float, float]] = {}
        for key in profile.priorities:
            rule = self.rules.get(key)
            if not rule or not rule.direction:
                continue
            vals = [float(v.product.attributes[rule.attr]) for v in views if isinstance(v.product.attributes.get(rule.attr), (int, float))]
            if vals:
                ranges[rule.attr] = (min(vals), max(vals))
        return ranges

    def _score(self, profile: UserProfile, v: ProductView, ranges: dict[str, tuple[float, float]]) -> ScoredProduct:
        p = v.product
        ex = Explainability()
        known, total_data = 0.0, 0.0
        comps: dict[str, float] = {}

        # --- budget
        price = v.ranking_price
        is_estimate = v.current_price is None
        total_data += 1
        if price is not None:
            known += 0.5 if is_estimate else 1.0
        if not profile.budget_max:
            comps["budget"] = 1.0
        elif price is None:
            comps["budget"] = 0.5
            ex.missing_features.append("prezzo non disponibile")
        elif price <= profile.budget_max:
            comps["budget"] = 1.0
            if profile.budget_min and price < profile.budget_min:
                comps["budget"] = 0.7
                ex.weak_matches.append("Sotto la fascia di prezzo che avevi indicato")
            if is_estimate:
                ex.reasons.append(f"Fascia di prezzo compatibile con il tuo budget di {_fmt_eur(profile.budget_max)}")
            else:
                ex.reasons.append(f"Rientra nel tuo budget di {_fmt_eur(profile.budget_max)}")
            ex.matched.append("budget")
        else:
            over = price - profile.budget_max
            tol = profile.budget_max * self.cfg.budget_tolerance or 1
            comps["budget"] = max(0.0, 1 - over / tol)
            if is_estimate:
                ex.penalties.append("Potrebbe superare leggermente il tuo budget")
            else:
                ex.penalties.append(f"Supera il tuo budget di circa {_fmt_eur(over)}")

        # --- use case
        if profile.use_cases:
            hit = [u for u in profile.use_cases if u in p.use_cases]
            comps["use_case"] = len(hit) / len(profile.use_cases)
            labels = self.cfg.use_case_labels
            if hit:
                ex.reasons.append("Adatta a: " + ", ".join(labels.get(u, u).lower() for u in hit))
                ex.matched.append("uso")
            for u in profile.use_cases:
                if u not in p.use_cases:
                    ex.weak_matches.append(f"Non specifica per: {labels.get(u, u).lower()}")
        else:
            comps["use_case"] = 1.0

        # --- esperienza
        if profile.experience and p.levels:
            lbl = self.cfg.experience_labels.get(profile.experience, profile.experience)
            if profile.experience in p.levels:
                comps["experience"] = 1.0
                ex.reasons.append(f"Indicata per il livello {lbl.lower()}")
            else:
                dist = min(
                    abs(EXPERIENCE_ORDER.index(profile.experience) - EXPERIENCE_ORDER.index(lv))
                    for lv in p.levels
                    if lv in EXPERIENCE_ORDER
                ) if profile.experience in EXPERIENCE_ORDER else 2
                comps["experience"] = 0.5 if dist == 1 else 0.2
                ex.weak_matches.append(f"Pensata per un livello diverso dal tuo ({lbl.lower()})")
        else:
            comps["experience"] = 1.0

        # --- priorità
        if profile.priorities:
            vals: list[tuple[float, float]] = []  # (punteggio, peso)
            for key in profile.priorities:
                rule = self.rules.get(key)
                if not rule:
                    continue
                total_data += 1
                raw = p.attributes.get(rule.attr)
                s = self._rule_score(rule, raw, ranges)
                pw = profile.priority_weights.get(key, 1.0)
                if s is None:
                    vals.append((0.3, pw))
                    ex.missing_features.append(f"{rule.label}: dato non disponibile")
                    continue
                known += 1
                vals.append((s, pw))
                text = rule.reason_template.format(value=_fmt_value(raw), unit=rule.unit or "").strip()
                if s >= 0.66:
                    ex.reasons.append(text)
                    ex.matched.append(rule.label)
                elif s <= 0.33:
                    ex.weak_matches.append(f"{rule.label}: non è il suo punto di forza")
            wsum_p = sum(w_ for _, w_ in vals)
            comps["priorities"] = sum(s_ * w_ for s_, w_ in vals) / wsum_p if wsum_p else 1.0
        else:
            comps["priorities"] = 1.0

        # --- requisiti (soft e hard già filtrati)
        soft = [r for r in profile.requirements if not r.hard]
        for r in profile.requirements:
            if r.hard:
                ex.reasons.append(f"Requisito rispettato: {r.label}")
                total_data += 1
                known += 1
        if soft:
            ok = 0.0
            for r in soft:
                total_data += 1
                res = eval_requirement(r, p.attributes)
                if res is True:
                    ok += 1
                    known += 1
                    ex.matched.append(r.label)
                    ex.reasons.append(f"Preferenza rispettata: {r.label}")
                elif res is False:
                    known += 1
                    ex.penalties.append(f"Preferenza non rispettata: {r.label}")
                else:
                    ok += 0.4
                    ex.missing_features.append(f"{r.label}: dato non disponibile")
            comps["requirements"] = ok / len(soft)
        else:
            comps["requirements"] = 1.0

        # --- combinazione pesata
        w = self.cfg.weights.model_dump()
        wsum = sum(w.values()) or 1
        score = 100 * sum(comps[k] * w[k] for k in w) / wsum

        partial_bad = [u for u in profile.use_cases if u in p.unsuitable_for]
        for u in partial_bad:
            score -= UNSUITABLE_PENALTY
            ex.penalties.append(f"Sconsigliata per: {self.cfg.use_case_labels.get(u, u).lower()}")
        if v.offer and v.offer.is_valid() and v.offer.price is None:
            score -= UNAVAILABLE_PENALTY
            ex.penalties.append("Al momento risulta non disponibile")
        score = max(0.0, min(100.0, score))

        ratio = known / total_data if total_data else 0
        confidence = "alta" if ratio >= 0.9 else "media" if ratio >= 0.6 else "bassa"

        return ScoredProduct(
            product_id=p.id,
            score=round(score, 1),
            components={k: round(v_, 3) for k, v_ in comps.items()},
            confidence=confidence,
            explain=ex,
            price_for_ranking=price,
            price_is_estimate=is_estimate,
        )

    @staticmethod
    def _rule_score(rule: PriorityRule, raw: Any, ranges: dict[str, tuple[float, float]]) -> float | None:
        if raw is None:
            return None
        if rule.direction:
            if not isinstance(raw, (int, float)):
                return None
            lo, hi = ranges.get(rule.attr, (float(raw), float(raw)))
            if hi == lo:
                return 1.0
            norm = (float(raw) - lo) / (hi - lo)
            return norm if rule.direction == "higher" else 1 - norm
        return 1.0 if raw == rule.equals else 0.0
