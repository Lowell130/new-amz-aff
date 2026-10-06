"""Il ranking deve dipendere dal profilo: 20 profili diversi, nessun vincitore fisso."""

import itertools

from app.models.finder import Requirement, UserProfile
from app.scoring.engine import ScoringEngine
from app.seed import trekking

from .conftest import make_services, run

FINDER = trekking.finder_definition()


def _views(fail=False):
    repos, _, pd, _ = make_services(fail)
    products = run(repos.products.all_in_category(FINDER.category))
    return run(pd.views(products))


VIEWS = _views()
BY_ID = {v.product.id: v for v in VIEWS}


def rank(profile):
    return ScoringEngine(FINDER).rank(profile, VIEWS)


PROFILES = [
    UserProfile(budget_max=b, experience=e, use_cases=[u], priorities=list(p))
    for (b, e, u, p) in itertools.islice(
        itertools.product(
            [80, 150, 300],
            ["beginner", "expert"],
            ["walk", "day_hike", "multi_day", "alpine"],
            [("lightweight",), ("durability", "grip")],
        ),
        0, None, 2,  # 24 combinazioni -> ne prendiamo una ogni due
    )
][:20]


def test_twenty_profiles_produce_varied_winners():
    assert len(PROFILES) == 20
    from collections import Counter

    winners = Counter()
    for prof in PROFILES:
        out = rank(prof)
        if out.ranked:
            winners[out.ranked[0].product_id] += 1
    assert len(winners) >= 6, f"Troppi vincitori uguali: {winners}"
    assert winners.most_common(1)[0][1] <= 8, "Un singolo prodotto vince quasi sempre"


def test_budget_changes_ranking_and_is_respected():
    low = rank(UserProfile(budget_max=80, use_cases=["day_hike"]))
    high = rank(UserProfile(budget_max=300, use_cases=["day_hike"], priorities=["durability"]))
    assert low.ranked[0].product_id != high.ranked[0].product_id
    for s in low.ranked:
        assert s.price_for_ranking <= 80 * (1 + FINDER.budget_tolerance)


def test_use_case_changes_ranking():
    walk = rank(UserProfile(use_cases=["walk"], priorities=["lightweight"]))
    alpine = rank(UserProfile(use_cases=["alpine"], priorities=["lightweight"]))
    assert walk.ranked[0].product_id != alpine.ranked[0].product_id
    top = BY_ID[alpine.ranked[0].product_id].product
    assert "alpine" in top.use_cases


def test_priority_changes_ranking():
    a = rank(UserProfile(use_cases=["day_hike"], priorities=["lightweight"]))
    b = rank(UserProfile(use_cases=["day_hike"], priorities=["durability"]))
    assert a.ranked[0].product_id != b.ranked[0].product_id
    wa = BY_ID[a.ranked[0].product_id].product.attributes["weight_g"]
    wb = BY_ID[b.ranked[0].product_id].product.attributes["weight_g"]
    assert wa < wb


def test_experience_changes_scores():
    beg = rank(UserProfile(experience="beginner", use_cases=["alpine"]))
    exp = rank(UserProfile(experience="expert", use_cases=["alpine"]))
    assert [s.score for s in beg.ranked] != [s.score for s in exp.ranked]


def test_hard_requirement_excludes():
    req = Requirement(attr="waterproof", op="eq", value=True, hard=True, label="impermeabile")
    out = rank(UserProfile(requirements=[req]))
    assert out.excluded > 0
    assert all(BY_ID[s.product_id].product.attributes["waterproof"] for s in out.ranked)


def test_reasons_are_grounded_in_data():
    out = rank(UserProfile(use_cases=["day_hike"], priorities=["waterproof", "lightweight"]))
    for s in out.ranked:
        attrs = BY_ID[s.product_id].product.attributes
        has_wp_reason = any(r.startswith("Impermeabile") for r in s.explain.reasons)
        assert has_wp_reason == bool(attrs["waterproof"])
        for r in s.explain.reasons:
            if r.startswith("Tra le più leggere"):
                assert str(attrs["weight_g"]) in r.replace(".", "")


def test_deterministic():
    p = UserProfile(budget_max=150, use_cases=["day_hike"], priorities=["comfort"])
    assert [s.product_id for s in rank(p).ranked] == [s.product_id for s in rank(p).ranked]


def test_works_without_provider_prices():
    views = _views(fail=True)
    assert all(v.offer is None for v in views)
    out = ScoringEngine(FINDER).rank(UserProfile(budget_max=150, use_cases=["walk"]), views)
    assert out.ranked and all(s.price_is_estimate for s in out.ranked)
