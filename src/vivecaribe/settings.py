"""Application settings via pydantic-settings BaseSettings."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from vivecaribe.domain.enums import BookingProvider
from vivecaribe.domain.errors import DomainError
from vivecaribe.infrastructure.integrations.gmail import GmailMailbox
from vivecaribe.infrastructure.integrations.outlook import OutlookMailbox

# Authorized-user JSON (and Outlook token files) live here locally — never commit.
MAILBOX_CREDENTIALS_DIR = Path("secrets")

# Non-secret booking-provider / mailbox config (committed with the repo).
BOOKING_PROVIDERS_YAML_PATH = Path("booking_providers.yaml")


def gmail_credentials_env_name(credentials_file: str) -> str:
    """Map ``vivecaribe_token.json`` → ``VIVECARIBE_GMAIL_TOKEN_JSON``."""
    name = Path(credentials_file).name
    if name.endswith("_token.json"):
        stem = name[: -len("_token.json")]
    else:
        stem = Path(name).stem
    return f"{stem.upper()}_GMAIL_TOKEN_JSON"


class MailboxConfig(BaseModel):
    """One booking channel's mailbox: name, credentials file, and named queries.

    ``credentials_file`` is the local filename under ``MAILBOX_CREDENTIALS_DIR``
    (e.g. ``vivecaribe_token.json``). On Vercel, the same JSON is read from the
    env var derived by ``gmail_credentials_env_name`` (e.g.
    ``VIVECARIBE_GMAIL_TOKEN_JSON``). Multiple booking providers may share the
    same file / env var when they share one inbox.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    mailbox_name: Literal["gmail", "outlook"]
    credentials_file: str
    queries: dict[str, str] = Field(default_factory=dict)
    _client: GmailMailbox | OutlookMailbox | None = PrivateAttr(default=None)

    @property
    def credentials_path(self) -> Path:
        """Path to this mailbox's credentials file under ``secrets/``."""
        return MAILBOX_CREDENTIALS_DIR / self.credentials_file

    @property
    def client(self) -> GmailMailbox | OutlookMailbox:
        """Build (and cache) the mailbox client for this config."""
        if self._client is not None:
            return self._client

        path = self.credentials_path
        if self.mailbox_name == "gmail":
            if path.exists():
                self._client = GmailMailbox(credentials_path=path)
            else:
                env_name = gmail_credentials_env_name(self.credentials_file)
                raw = os.getenv(env_name)
                if not raw or not raw.strip():
                    raise DomainError(
                        f"Gmail credentials missing: no file at {path} and "
                        f"env var {env_name} is unset (set it on Vercel)",
                    )
                self._client = GmailMailbox(credentials_json=raw)
        else:
            token = path.read_text(encoding="utf-8").strip() if path.is_file() else None
            if token is None:
                env_name = Path(self.credentials_file).stem.upper()
                token = os.getenv(env_name)
            self._client = OutlookMailbox(access_token=token)
        return self._client


class BookingProviderAccount(BaseModel):
    """One booking provider and the mailbox that receives its emails."""

    booking_provider: BookingProvider
    mailbox: MailboxConfig


class BookingProvidersFile(BaseModel):
    """Root shape of booking_providers.yaml."""

    booking_providers: list[BookingProviderAccount] = Field(default_factory=list)


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

    def load_booking_providers(self) -> BookingProvidersFile:
        """Load non-secret booking-provider / mailbox config from YAML."""
        path = BOOKING_PROVIDERS_YAML_PATH
        if not path.is_file():
            return BookingProvidersFile()

        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return BookingProvidersFile.model_validate(raw)


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()
