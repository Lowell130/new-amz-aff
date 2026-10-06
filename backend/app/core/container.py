"""Composizione delle dipendenze in base alla configurazione."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.ai.advisor_llm import AdvisorLLM
from app.ai.base import LLMProvider, NullLLMProvider
from app.core.config import Settings
from app.providers.amazon_creators import AmazonCreatorsProvider
from app.providers.base import ProductProvider
from app.providers.mock import MockProductProvider
from app.repositories.base import Repositories
from app.repositories.memory import memory_repositories
from app.seed.loader import demo_catalog, seed_demo
from app.services.affiliate import AffiliateLinkService
from app.services.advisor import AdvisorService
from app.services.configurator import ConfiguratorService
from app.services.finder import FinderService
from app.services.product_data import ProductDataService

log = logging.getLogger(__name__)


@dataclass
class Container:
    settings: Settings
    repos: Repositories
    provider: ProductProvider
    affiliate: AffiliateLinkService
    product_data: ProductDataService
    finder: FinderService
    configurator: ConfiguratorService
    advisor: AdvisorService
    llm: LLMProvider
    _closers: list[Any] = field(default_factory=list)

    async def close(self) -> None:
        for c in self._closers:
            await c.close()


def _secret(v) -> str | None:
    return v.get_secret_value() if v else None


def build_provider(settings: Settings) -> ProductProvider:
    if settings.product_provider == "amazon":
        return AmazonCreatorsProvider(
            credential_id=_secret(settings.amazon_creators_credential_id),
            credential_secret=_secret(settings.amazon_creators_credential_secret),
            partner_tag=settings.amazon_partner_tag,
        )
    # Il mock conosce il catalogo demo per generare prezzi plausibili.
    return MockProductProvider(demo_catalog(), ttl_hours=settings.provider_cache_ttl_hours)


def build_llm(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "none":
        return NullLLMProvider()
    from app.ai.providers import GeminiProvider, OpenAIProvider

    key = _secret(settings.llm_api_key) or ""
    model = settings.llm_model or ""
    if settings.llm_provider == "openai":
        return OpenAIProvider(key, model)
    return GeminiProvider(key, model)


async def build_container(settings: Settings, repos: Repositories | None = None) -> Container:
    closers: list[Any] = []
    if repos is None:
        if settings.data_backend == "mongo":
            from app.db.mongo import create_client, ensure_indexes
            from app.repositories.mongo import mongo_repositories

            client = create_client(settings.mongo_uri.get_secret_value())
            db = client[settings.mongo_db]
            await ensure_indexes(db)
            repos = mongo_repositories(db)
            closers.append(client)
        else:
            repos = memory_repositories()

    if settings.seed_demo_on_startup:
        stats = await seed_demo(repos)
        log.info("Dataset demo caricato: %s", stats)

    provider = build_provider(settings)
    affiliate = AffiliateLinkService(settings.amazon_partner_tag, settings.amazon_marketplace)
    product_data = ProductDataService(provider, repos.snapshots, affiliate)
    llm = build_llm(settings)
    finder = FinderService(repos, product_data)
    configurator = ConfiguratorService(repos, product_data)
    return Container(
        settings=settings,
        repos=repos,
        provider=provider,
        affiliate=affiliate,
        product_data=product_data,
        finder=finder,
        configurator=configurator,
        advisor=AdvisorService(repos, finder, configurator, AdvisorLLM(llm)),
        llm=llm,
        _closers=closers,
    )
