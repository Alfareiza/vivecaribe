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
from vivecaribe.infrastructure.integrations.zoho import ZohoMailbox

# Non-secret booking-provider / mailbox config (committed with the repo).
BOOKING_PROVIDERS_YAML_PATH = Path("booking_providers.yaml")


class MailboxConfig(BaseModel):
    """One booking channel's mailbox: name, credential env vars, and queries.

    ``credentials_vars`` maps logical keys to environment-variable names, e.g.::

        credentials_vars:
          token: GYG_GMAIL_TOKEN
          refresh_token: GYG_GMAIL_REFRESH_TOKEN

    Shared OAuth app credentials (``GMAIL_CLIENT_*`` / ``OUTLOOK_CLIENT_*``)
    live on ``Settings``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    mailbox_name: Literal["gmail", "outlook", "zoho"]
    credentials_vars: dict[str, str] = Field(default_factory=dict)
    queries: dict[str, str] = Field(default_factory=dict)
    _client: GmailMailbox | OutlookMailbox | ZohoMailbox | None = PrivateAttr(
        default=None,
    )

    @property
    def client(self) -> GmailMailbox | OutlookMailbox | ZohoMailbox:
        """Build (and cache) the mailbox client for this config."""
        if self._client is not None:
            return self._client

        settings = get_settings()
        if self.mailbox_name == "gmail":
            self._client = GmailMailbox(
                token=settings.require_env(self._var("token")),
                refresh_token=settings.require_env(self._var("refresh_token")),
                client_id=settings.require_gmail_client_id(),
                client_secret=settings.require_gmail_client_secret(),
            )
        elif self.mailbox_name == "outlook":
            self._client = OutlookMailbox(
                client_id=settings.require_outlook_client_id(),
                client_secret=settings.require_outlook_client_secret(),
                refresh_token=settings.require_env(self._var("refresh_token")),
            )
        else:
            self._client = ZohoMailbox(
                username=settings.require_env(self._var("username")),
                password=settings.require_env(self._var("password")),
            )
        return self._client

    def _var(self, key: str) -> str:
        """Return the env-var name mapped for ``key`` in ``credentials_vars``."""
        name = self.credentials_vars.get(key)
        if not name or not name.strip():
            raise DomainError(
                f"Mailbox credentials_vars missing key {key!r} "
                f"for mailbox_name={self.mailbox_name!r}",
            )
        return name.strip()


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

    gmail_client_id: SecretStr | None = None
    gmail_client_secret: SecretStr | None = None
    outlook_client_id: SecretStr | None = None
    outlook_client_secret: SecretStr | None = None

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

    @field_validator(
        "gmail_client_id",
        "gmail_client_secret",
        "outlook_client_id",
        "outlook_client_secret",
        mode="before",
    )
    @classmethod
    def empty_oauth_secret_as_none(cls, value: object) -> object:
        """Treat blank OAuth secrets as unset."""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return None
        return value

    @staticmethod
    def require_env(name: str) -> str:
        """Return a required environment variable or raise ``DomainError``."""
        value = os.getenv(name)
        if not value or not value.strip():
            raise DomainError(f"Environment variable {name} is unset")
        return value.strip()

    def require_gmail_client_id(self) -> str:
        """Return ``GMAIL_CLIENT_ID`` or raise if unset."""
        if self.gmail_client_id is None:
            raise DomainError("GMAIL_CLIENT_ID is not configured")
        return self.gmail_client_id.get_secret_value()

    def require_gmail_client_secret(self) -> str:
        """Return ``GMAIL_CLIENT_SECRET`` or raise if unset."""
        if self.gmail_client_secret is None:
            raise DomainError("GMAIL_CLIENT_SECRET is not configured")
        return self.gmail_client_secret.get_secret_value()

    def require_outlook_client_id(self) -> str:
        """Return ``OUTLOOK_CLIENT_ID`` or raise if unset."""
        if self.outlook_client_id is None:
            raise DomainError("OUTLOOK_CLIENT_ID is not configured")
        return self.outlook_client_id.get_secret_value()

    def require_outlook_client_secret(self) -> str:
        """Return ``OUTLOOK_CLIENT_SECRET`` or raise if unset."""
        if self.outlook_client_secret is None:
            raise DomainError("OUTLOOK_CLIENT_SECRET is not configured")
        return self.outlook_client_secret.get_secret_value()

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
    from dotenv import load_dotenv

    # Load undeclared per-mailbox keys into ``os.environ`` for ``require_env``.
    load_dotenv()
    return Settings()
