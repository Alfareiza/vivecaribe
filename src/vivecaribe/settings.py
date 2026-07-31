"""Application settings via pydantic-settings BaseSettings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AccountQuery(BaseModel):
    """Search query associated with a mailbox account."""

    label: str
    query: str


class AccountConfig(BaseModel):
    """Non-secret mailbox account definition (credentials live in env)."""

    name: str
    provider: Literal["gmail", "outlook"]
    queries: list[AccountQuery] = Field(default_factory=list)


class AccountsFile(BaseModel):
    """Root shape of accounts.yaml."""

    accounts: list[AccountConfig] = Field(default_factory=list)


class Settings(BaseSettings):
    """Env-backed settings for the ViveCaribe API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["local", "staging", "prod"] = "local"
    log_level: str = "INFO"

    database_url: SecretStr
    jwt_secret: SecretStr
    jwt_expire_minutes: int = 60
    cron_secret: SecretStr
    sentry_dsn: str | None = None

    accounts_yaml_path: Path = Path("accounts.yaml")

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normalize log level names to uppercase (e.g. ``info`` → ``INFO``)."""
        return value.upper()

    @field_validator("sentry_dsn")
    @classmethod
    def empty_sentry_dsn_as_none(cls, value: str | None) -> str | None:
        """Treat blank ``SENTRY_DSN`` values as unset (``None``)."""
        if value is None or value.strip() == "":
            return None
        return value

    def load_accounts(self) -> AccountsFile:
        """Load non-secret account/query config from YAML."""
        path = self.accounts_yaml_path
        if not path.is_file():
            return AccountsFile()

        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return AccountsFile.model_validate(raw)


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()
