"""Dalla classifica alle "caselle" mostrate all'utente.

Le etichette sono SEMPRE contestuali al profilo, mai "migliore/peggiore" in assoluto.
"""

from __future__ import annotations

from app.models.finder import RecommendationSlot, ScoredProduct

LABELS = {
    "best_match": "La scelta più adatta al tuo profilo",
    "cheaper": "Alternativa con prezzo inferiore",
    "premium": "Alternativa orientata alla massima dotazione",
    "alternative": "Altra opzione compatibile",
}


def build_slots(ranked: list[ScoredProduct], max_items: int = 6) -> list[RecommendationSlot]:
    if not ranked:
        return []
    best = ranked[0]
    used = {best.product_id}
    slots = [RecommendationSlot(role="best_match", label=LABELS["best_match"], scored=best)]
    bp = best.price_for_ranking

    if bp is not None:
        cheaper = [
            s for s in ranked[1:]
            if s.price_for_ranking is not None
            and s.price_for_ranking < bp * 0.85
            and s.score >= best.score * 0.75
        ]
        if cheaper:
            c = cheaper[0]  # già ordinati per punteggio
            slots.append(RecommendationSlot(role="cheaper", label=LABELS["cheaper"], scored=c))
            used.add(c.product_id)

        premium = [
            s for s in ranked[1:]
            if s.product_id not in used
            and s.price_for_ranking is not None
            and s.price_for_ranking > bp * 1.1
            and s.score >= best.score * 0.75
        ]
        if premium:
            pr = max(
                premium,
                key=lambda s: (s.components.get("priorities", 0) + s.components.get("requirements", 0), s.score),
            )
            slots.append(RecommendationSlot(role="premium", label=LABELS["premium"], scored=pr))
            used.add(pr.product_id)

    for s in ranked[1:]:
        if len(slots) >= max_items:
            break
        if s.product_id in used:
            continue
        slots.append(RecommendationSlot(role="alternative", label=LABELS["alternative"], scored=s))
        used.add(s.product_id)
    return slots
