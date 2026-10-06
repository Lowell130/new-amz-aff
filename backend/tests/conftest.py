import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.providers.mock import MockProductProvider  # noqa: E402
from app.repositories.memory import memory_repositories  # noqa: E402
from app.seed import trekking  # noqa: E402
from app.seed.loader import demo_catalog, seed_demo  # noqa: E402
from app.services.affiliate import AffiliateLinkService  # noqa: E402
from app.services.finder import FinderService  # noqa: E402
from app.services.product_data import ProductDataService  # noqa: E402


def run(coro):
    return asyncio.run(coro)


def make_services(fail_provider: bool = False):
    repos = memory_repositories()
    run(seed_demo(repos))
    provider = MockProductProvider(demo_catalog(), fail=fail_provider)
    pd = ProductDataService(provider, repos.snapshots, AffiliateLinkService("test-21"))
    return repos, provider, pd, FinderService(repos, pd)


def make_advisor(llm_provider=None):
    from app.ai.advisor_llm import AdvisorLLM
    from app.services.advisor import AdvisorService
    from app.services.configurator import ConfiguratorService

    repos, _, pd, finder = make_services()
    return repos, AdvisorService(repos, finder, ConfiguratorService(repos, pd), AdvisorLLM(llm_provider))
