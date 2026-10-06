"""Configurazione: SOLO da variabili d'ambiente / file .env. Nessuna credenziale nel codice."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    app_url: str = "http://localhost:3000"
    log_level: str = "INFO"

    # memory = nessun MongoDB necessario (dati demo caricati all'avvio)
    data_backend: Literal["memory", "mongo"] = "memory"
    mongo_uri: SecretStr = SecretStr("mongodb://localhost:27017")
    mongo_db: str = "product_discovery"
    seed_demo_on_startup: bool = True

    product_provider: Literal["mock", "amazon"] = "mock"
    provider_cache_ttl_hours: float = Field(default=24, gt=0, le=24)  # regola Amazon: max 24h

    amazon_partner_tag: str | None = None
    amazon_marketplace: str = "it"
    amazon_creators_credential_id: SecretStr | None = None
    amazon_creators_credential_secret: SecretStr | None = None

    llm_provider: Literal["none", "openai", "gemini"] = "none"
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None

    cors_origins: str = "http://localhost:3000"  # separati da virgola
    admin_token: SecretStr | None = None
    rate_limit_per_minute: int = 120

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
