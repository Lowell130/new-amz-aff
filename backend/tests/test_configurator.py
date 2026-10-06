"""Configuratore: budget, incompatibilità, riproducibilità, variazione col budget, sostituzioni."""

import itertools

import pytest

from app.scoring.configurator import BudgetTooLow, ComponentNotFound, incompatible
from app.scoring.flow import InvalidAnswer
from app.services.configurator import ConfiguratorService

from .conftest import make_services, run

BASE = {"use": "day_hike", "experience": "beginner", "weather": "mixed", "priorities": ["comfort"]}


def svc():
    repos, _, pd, _ = make_services()
    return repos, ConfiguratorService(repos, pd)


def build(answers, optional=None):
    repos, s = svc()
    return repos, s, run(s.build("kit-trekking", answers, optional))


@pytest.mark.parametrize("budget", [250, 400, 600, 900, 1500])
def test_budget_is_never_exceeded(budget):
    _, _, sess = build({**BASE, "budget": budget})
    r = sess.result
    assert r.total_for_ranking <= budget
    assert not r.over_budget
    keys = {it.component_key for it in r.items}
    assert {"scarpe", "zaino", "giacca"} <= keys  # essenziali sempre presenti


def test_budget_changes_configuration():
    kits = []
    for b in (350, 600, 1000):
        _, _, sess = build({**BASE, "use": "multi_day", "budget": b})
        kits.append(tuple(it.scored.product_id for it in sess.result.items))
    assert len(set(kits)) == 3


def test_reproducible():
    a = build({**BASE, "budget": 500})[2].result
    b = build({**BASE, "budget": 500})[2].result
    assert [i.scored.product_id for i in a.items] == [i.scored.product_id for i in b.items]
    assert a.total_for_ranking == b.total_for_ranking


def test_budget_too_low():
    _, s = svc()
    with pytest.raises(BudgetTooLow) as e:
        run(s.build("kit-trekking", {**BASE, "budget": 100}, None))
    assert e.value.min_needed > 100


def test_incompatibilities_are_respected():
    repos, s = svc()
    for use, budget in itertools.product(["walk", "day_hike", "multi_day"], [200, 300, 450, 700]):
        try:
            sess = run(s.build("kit-trekking", {**BASE, "use": use, "budget": budget}, None))
        except BudgetTooLow:
            continue
        products = run(repos.products.get_many([it.scored.product_id for it in sess.result.items]))
        for a, b in itertools.combinations(products, 2):
            assert not incompatible(a, b), (a.id, b.id)


def test_hard_requirements_apply_to_right_components():
    repos, _, sess = build({**BASE, "weather": "wet", "budget": 900})
    by_comp = {it.component_key: it.scored.product_id for it in sess.result.items}
    shoes, jacket = run(repos.products.get_many([by_comp["scarpe"], by_comp["giacca"]]))
    assert shoes.attributes["waterproof"] and jacket.attributes["waterproof"]


def test_optional_components_selection():
    _, _, sess = build({**BASE, "budget": 900}, optional=[])
    assert {it.component_key for it in sess.result.items} == {"scarpe", "zaino", "giacca"}
    _, s = svc()
    with pytest.raises(InvalidAnswer):
        run(s.build("kit-trekking", {**BASE, "budget": 900}, ["scarpe"]))


def test_alternatives_and_swap():
    repos, s, sess = build({**BASE, "budget": 400})
    item = next(it for it in sess.result.items if it.downgrade or it.upgrade)
    alt = item.downgrade or item.upgrade
    assert alt.product_id != item.scored.product_id
    if item.downgrade:
        assert item.downgrade.price_for_ranking < item.scored.price_for_ranking
    if item.upgrade:
        assert item.upgrade.score > item.scored.score

    swapped = run(s.swap(sess.session_id, item.component_key, alt.product_id))
    new = next(it for it in swapped.result.items if it.component_key == item.component_key)
    assert new.scored.product_id == alt.product_id
    expected = sum(it.scored.price_for_ranking for it in swapped.result.items)
    assert abs(swapped.result.total_for_ranking - expected) < 0.01
    assert swapped.result.over_budget == (expected > 400)

    with pytest.raises(ComponentNotFound):
        run(s.swap(sess.session_id, "scarpe", "prodotto-inesistente"))


def test_present_uses_only_valid_prices():
    repos, s, sess = build({**BASE, "budget": 500})
    t = run(s.get_template("kit-trekking"))
    p = run(s.present(sess, t))
    valid = [pi.view.current_price for pi in p.items if pi.view.current_price is not None]
    assert abs(p.total_valid - sum(valid)) < 0.01
    assert (p.residual is None) == (p.missing_prices > 0)
