"""Test end-to-end delle API (richiede fastapi + httpx installati)."""

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture()
def client():
    settings = Settings(_env_file=None, data_backend="memory", amazon_partner_tag="test-21", admin_token="segreto")
    with TestClient(create_app(settings)) as c:
        yield c


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_finder_flow(client):
    finders = client.get("/api/finders").json()
    assert finders[0]["slug"] == "scarpe-trekking"
    st = client.post("/api/finder/scarpe-trekking/start").json()
    answers = {"use": "day_hike", "experience": "beginner", "weather": "mixed", "ankle": "mid",
               "priorities": ["comfort"], "wide": True, "budget": 150}
    while not st["done"]:
        qid = st["question"]["id"]
        r = client.post(f"/api/finder/session/{st['session_id']}/answer", json={"question_id": qid, "value": answers[qid]})
        assert r.status_code == 200, r.text
        st = r.json()
    res = client.post(f"/api/finder/session/{st['session_id']}/complete").json()
    assert res["slots"][0]["role"] == "best_match"
    assert res["slots"][0]["product"]["affiliate_url"].endswith("tag=test-21")
    assert client.get(f"/api/finder/session/{st['session_id']}/result").status_code == 200


def test_invalid_answer(client):
    st = client.post("/api/finder/scarpe-trekking/start").json()
    r = client.post(f"/api/finder/session/{st['session_id']}/answer", json={"question_id": "use", "value": "x"})
    assert r.status_code == 422


def test_events_are_sanitized_and_admin_protected(client):
    r = client.post("/api/events", json={"type": "affiliate_link_clicked", "payload": {"asin": "DEMO000001", "email": "x@y.z"}})
    assert r.status_code == 204
    assert client.get("/api/admin/stats").status_code == 401
    stats = client.get("/api/admin/stats", headers={"X-Admin-Token": "segreto"}).json()
    assert stats["events"]["affiliate_link_clicked"] == 1


def test_configurator_api(client):
    assert client.get("/api/configurators").json()[0]["slug"] == "kit-trekking"
    detail = client.get("/api/configurators/kit-trekking").json()
    assert [q["id"] for q in detail["inputs"]][0] == "use"
    body = {"answers": {"use": "day_hike", "experience": "beginner", "weather": "mixed", "budget": 450}}
    r = client.post("/api/configurators/kit-trekking/build", json=body)
    assert r.status_code == 200, r.text
    cfg = r.json()
    assert cfg["total_valid"] <= 450 and cfg["items"]
    item = next(i for i in cfg["items"] if i["downgrade"] or i["upgrade"])
    alt = item["downgrade"] or item["upgrade"]
    r2 = client.post(f"/api/configuration/{cfg['session_id']}/swap",
                     json={"component_key": item["component_key"], "product_id": alt["product"]["id"]})
    assert r2.status_code == 200, r2.text
    assert client.get(f"/api/configuration/{cfg['session_id']}").status_code == 200


def test_configurator_budget_too_low(client):
    r = client.post("/api/configurators/kit-trekking/build", json={"answers": {"use": "multi_day", "experience": "beginner", "weather": "dry", "budget": 100}})
    assert r.status_code == 422
    assert "servono almeno" in r.json()["detail"]
