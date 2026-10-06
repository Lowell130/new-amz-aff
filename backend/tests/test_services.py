from datetime import timedelta

import pytest

from app.models.product import ProviderSnapshot, utcnow
from app.services.affiliate import AffiliateLinkError, AffiliateLinkService
from app.services.product_data import ProductDataService

from .conftest import make_services, run


def test_affiliate_link():
    s = AffiliateLinkService("mio-tag-21")
    assert s.build("b0abc12345") == "https://www.amazon.it/dp/B0ABC12345?tag=mio-tag-21"
    assert s.build("B0ABC12345", "de").startswith("https://www.amazon.de/")
    with pytest.raises(AffiliateLinkError):
        s.build("abc")
    with pytest.raises(AffiliateLinkError):
        AffiliateLinkService("tag con spazi")


def test_snapshots_are_reused_until_expiry():
    repos, provider, pd, _ = make_services()
    products = run(repos.products.all_in_category("scarpe-trekking"))[:25]
    run(pd.views(products))
    calls = provider.calls
    run(pd.views(products))
    assert provider.calls == calls  # seconda volta: tutto dalla cache valida


def test_provider_failure_is_failsafe():
    repos, _, pd, _ = make_services(fail_provider=True)
    products = run(repos.products.all_in_category("scarpe-trekking"))[:5]
    views = run(pd.views(products))
    assert all(v.offer is None and v.current_price is None for v in views)
    assert all(v.affiliate_url for v in views)


def test_ttl_is_capped_to_24h():
    now = utcnow()
    s = ProviderSnapshot(asin="DEMO000001", source="x", fetched_at=now, expires_at=now + timedelta(days=7))
    assert ProductDataService._cap_ttl(s).expires_at == now + timedelta(hours=24)


def test_expired_snapshot_not_valid():
    now = utcnow()
    s = ProviderSnapshot(asin="DEMO000001", source="x", fetched_at=now - timedelta(hours=30),
                         expires_at=now - timedelta(hours=6))
    assert not s.is_valid()
