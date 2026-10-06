"""Motore del Configuratore: sceglie UN prodotto per componente massimizzando la qualità
complessiva del kit, senza superare il budget e rispettando le incompatibilità.

Passi:
1. per ogni componente, il profilo utente viene "ritagliato" (solo i requisiti e le priorità
   pertinenti) e i prodotti della categoria vengono classificati con lo ScoringEngine;
2. per ogni componente si tiene la frontiera prezzo/qualità (si scartano i prodotti peggiori
   E più cari di un altro);
3. una ricerca branch-and-bound esatta trova la combinazione di valore massimo entro il budget,
   rispettando le incompatibilità tra prodotti;
4. per ogni componente scelto si calcolano alternative upgrade/downgrade compatibili.

Tutto è deterministico: stesso input -> stesso kit.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.configurator import (
    ComponentSpec,
    ConfigItem,
    ConfigurationResult,
    ConfigurationTemplate,
    SkippedComponent,
)
from app.models.finder import ScoredProduct, ScoringConfig, UserProfile
from app.models.product import Product, ProductView, utcnow
from app.scoring.engine import ScoringEngine

UPGRADE_MIN_GAIN = 0.5  # punti di score
DOWNGRADE_MIN_RATIO = 0.75
# Gli opzionali possono entrare solo se la qualità degli essenziali resta almeno a questa
# quota del massimo ottenibile con lo stesso budget (prima l'essenziale, poi gli accessori).
ESSENTIALS_MIN_SHARE = 0.92  # un downgrade deve restare almeno al 75% del punteggio attuale


class BudgetTooLow(Exception):
    def __init__(self, min_needed: float):
        self.min_needed = min_needed
        super().__init__(f"Budget insufficiente: servono almeno circa {min_needed:.0f} €")


class ComponentNotFound(Exception):
    pass


@dataclass(frozen=True)
class Candidate:
    product: Product
    scored: ScoredProduct

    @property
    def price(self) -> float:
        return float(self.scored.price_for_ranking or 0)

    @property
    def score(self) -> float:
        return self.scored.score


def incompatible(a: Product, b: Product) -> bool:
    a_marks = set(a.tags) | {a.id}
    b_marks = set(b.tags) | {b.id}
    return bool(set(a.incompatible_with) & b_marks or set(b.incompatible_with) & a_marks)


def _compatible_with_all(c: Candidate, others: list[Candidate]) -> bool:
    return all(not incompatible(c.product, o.product) for o in others)


class ConfigurationEngine:
    def __init__(self, template: ConfigurationTemplate):
        self.t = template

    # ------------------------------------------------------------ candidati
    def component_profile(self, profile: UserProfile, comp: ComponentSpec) -> UserProfile:
        keys = {r.key for r in comp.priority_rules}
        user = [p for p in profile.priorities if p in keys]
        defaults = [p for p in comp.default_priorities if p in keys and p not in user]
        return UserProfile(
            experience=profile.experience,
            use_cases=list(profile.use_cases),
            priorities=user + defaults,
            priority_weights={**{p: 1.0 for p in defaults}, **{p: 2.0 for p in user}},
            requirements=[r for r in profile.requirements if r.attr in comp.requirement_attrs],
        )

    def candidates(self, profile: UserProfile, comp: ComponentSpec, views: list[ProductView]) -> list[Candidate]:
        cfg = ScoringConfig(
            priority_rules=comp.priority_rules,
            use_case_labels=self.t.use_case_labels,
            experience_labels=self.t.experience_labels,
            weights=self.t.weights,
        )
        ranking = ScoringEngine(cfg).rank(self.component_profile(profile, comp), views)
        by_id = {v.product.id: v.product for v in views}
        return [
            Candidate(by_id[s.product_id], s)
            for s in ranking.ranked
            if s.price_for_ranking is not None
        ]

    @staticmethod
    def frontier(cands: list[Candidate], watched: set[str]) -> list[Candidate]:
        """Frontiera prezzo/qualità: scarta i prodotti "dominati" (un altro costa uguale o meno
        e ha punteggio uguale o maggiore). Il confronto avviene solo tra prodotti con la stessa
        "firma" di compatibilità, per non perdere opzioni utili a evitare incompatibilità."""
        groups: dict[tuple, list[Candidate]] = {}
        for c in cands:
            sig = (frozenset(set(c.product.tags) & watched), frozenset(c.product.incompatible_with))
            groups.setdefault(sig, []).append(c)
        out: list[Candidate] = []
        for g in groups.values():
            best_score = -1.0
            for c in sorted(g, key=lambda c: (c.price, -c.score, c.product.id)):
                if c.score > best_score + 1e-9:
                    out.append(c)
                    best_score = c.score
        return sorted(out, key=lambda c: (-c.score, c.price, c.product.id))

    # -------------------------------------------------------------- build
    def build(
        self,
        profile: UserProfile,
        budget: float,
        cands_by_comp: dict[str, list[Candidate]],
        include_optional: list[str] | None = None,
    ) -> ConfigurationResult:
        comps: list[ComponentSpec] = []
        skipped: list[SkippedComponent] = []
        for c in self.t.components:
            if not c.required and include_optional is not None and c.key not in include_optional:
                continue
            if not cands_by_comp.get(c.key):
                skipped.append(SkippedComponent(component_key=c.key, label=c.label,
                                                reason="Nessun prodotto compatibile con le tue risposte"))
                continue
            comps.append(c)
        comps.sort(key=lambda c: (not c.required, -c.weight, c.key))

        watched = {m for cs in cands_by_comp.values() for c in cs for m in c.product.incompatible_with}
        options: list[list[Candidate | None]] = []
        for c in comps:
            opts: list[Candidate | None] = list(self.frontier(cands_by_comp[c.key], watched))
            if not c.required:
                opts.append(None)
            options.append(opts)

        n_req = sum(1 for c in comps if c.required)
        ess = self._search(comps[:n_req], options[:n_req], budget)
        best_combo = None
        if ess is not None:
            ess_value = sum(c.weight * x.score / 100 for c, x in zip(comps, ess) if x is not None)
            best_combo = self._search(comps, options, budget, n_req=n_req,
                                      essentials_floor=ess_value * ESSENTIALS_MIN_SHARE)
        if best_combo is None:
            need = sum(min(x.price for x in cands_by_comp[c.key]) for c in comps if c.required)
            raise BudgetTooLow(max(need, budget + 1))

        items: list[ConfigItem] = []
        for c, x in zip(comps, best_combo):
            if x is None:
                skipped.append(SkippedComponent(component_key=c.key, label=c.label,
                                                reason="Non rientrava nel budget senza sacrificare i componenti essenziali"))
                continue
            items.append(ConfigItem(component_key=c.key, label=c.label, required=c.required, scored=x.scored))
        order = {c.key: i for i, c in enumerate(self.t.components)}
        items.sort(key=lambda it: order[it.component_key])

        result = ConfigurationResult(
            profile=profile, budget=budget, items=items, skipped=skipped,
            total_for_ranking=0, generated_at=utcnow(),
        )
        return self.refresh(result, cands_by_comp)

    @staticmethod
    def _search(
        comps: list[ComponentSpec],
        options: list[list[Candidate | None]],
        budget: float,
        n_req: int = 0,
        essentials_floor: float = 0.0,
    ) -> tuple[Candidate | None, ...] | None:
        """Branch and bound esatto: massimizza sum(peso * score) con totale <= budget.
        A parità di valore preferisce il kit meno costoso, poi l'ordine degli id (determinismo)."""
        n = len(comps)

        def cost(x): return x.price if x else 0.0
        def val(i, x): return comps[i].weight * x.score / 100 if x else 0.0

        min_cost = [0.0] * (n + 1)
        max_val = [0.0] * (n + 1)
        for i in range(n - 1, -1, -1):
            min_cost[i] = min_cost[i + 1] + min(cost(x) for x in options[i])
            max_val[i] = max_val[i + 1] + max(val(i, x) for x in options[i])

        best: dict = {"key": None, "combo": None}
        chosen: list[Candidate | None] = []

        def rec(i: int, v: float, total: float) -> None:
            if i == n_req and v < essentials_floor - 1e-9:
                return  # essenziali troppo sacrificati a favore degli opzionali
            if i == n:
                key = (-round(v, 6), round(total, 2), tuple(x.product.id if x else "" for x in chosen))
                if best["key"] is None or key < best["key"]:
                    best["key"], best["combo"] = key, tuple(chosen)
                return
            for x in options[i]:
                t = total + cost(x)
                if t + min_cost[i + 1] > budget + 1e-9:
                    continue
                nv = v + val(i, x)
                if best["key"] is not None and -(nv + max_val[i + 1]) > best["key"][0] + 1e-9:
                    continue  # anche col meglio possibile non si batte il kit migliore trovato
                if x is not None and any(o is not None and incompatible(x.product, o.product) for o in chosen):
                    continue
                chosen.append(x)
                rec(i + 1, nv, t)
                chosen.pop()

        rec(0, 0.0, 0.0)
        return best["combo"]

    # -------------------------------------------------- alternative / swap
    def refresh(self, result: ConfigurationResult, cands_by_comp: dict[str, list[Candidate]]) -> ConfigurationResult:
        """Ricalcola totale e alternative upgrade/downgrade per ogni componente."""
        current = {it.component_key: self._find(cands_by_comp, it.component_key, it.scored.product_id) for it in result.items}
        total = sum(c.price for c in current.values())
        residual = result.budget - total
        new_items = []
        for it in result.items:
            cur = current[it.component_key]
            others = [c for k, c in current.items() if k != it.component_key]
            alts = [c for c in cands_by_comp[it.component_key]
                    if c.product.id != cur.product.id and _compatible_with_all(c, others)]

            cheaper = [c for c in alts if c.price < cur.price and c.score >= cur.score * DOWNGRADE_MIN_RATIO]
            down = max(cheaper, key=lambda c: (c.score, -c.price), default=None)

            better = [c for c in alts if c.score >= cur.score + UPGRADE_MIN_GAIN and c.price > cur.price]
            fitting = [c for c in better if c.price - cur.price <= residual + 1e-9]
            if fitting:
                up = max(fitting, key=lambda c: (c.score, -c.price))
            else:
                up = min(better, key=lambda c: (c.price, -c.score), default=None)

            new_items.append(it.model_copy(update={
                "scored": cur.scored,
                "upgrade": up.scored if up else None,
                "downgrade": down.scored if down else None,
            }))
        return result.model_copy(update={
            "items": new_items,
            "total_for_ranking": round(total, 2),
            "over_budget": total > result.budget + 1e-9,
        })

    def swap(
        self, result: ConfigurationResult, cands_by_comp: dict[str, list[Candidate]], component_key: str, product_id: str
    ) -> ConfigurationResult:
        if component_key not in {it.component_key for it in result.items}:
            raise ComponentNotFound(f"Componente '{component_key}' non presente nel kit")
        new = self._find(cands_by_comp, component_key, product_id)
        others = [self._find(cands_by_comp, it.component_key, it.scored.product_id)
                  for it in result.items if it.component_key != component_key]
        if not _compatible_with_all(new, others):
            raise ComponentNotFound("Il prodotto scelto non è compatibile con il resto del kit")
        items = [it.model_copy(update={"scored": new.scored}) if it.component_key == component_key else it
                 for it in result.items]
        return self.refresh(result.model_copy(update={"items": items}), cands_by_comp)

    @staticmethod
    def _find(cands_by_comp: dict[str, list[Candidate]], key: str, product_id: str) -> Candidate:
        for c in cands_by_comp.get(key, []):
            if c.product.id == product_id:
                return c
        raise ComponentNotFound(f"Prodotto '{product_id}' non disponibile per '{key}'")
