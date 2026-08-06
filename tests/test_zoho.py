"""Unit tests for Zoho session / mail helpers (no live browser)."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vivecaribe.domain.errors import DomainError
from vivecaribe.infrastructure.integrations.zoho import (
    ACCOUNT_ID,
    ZohoMailClient,
    ZohoMailbox,
    ZohoSession,
)
from vivecaribe.settings import MailboxConfig, get_settings


def _session(tmp_path: Path) -> ZohoSession:
    """Build a ZohoSession with an isolated session path."""
    return ZohoSession(
        "user@example.com",
        "secret",
        session_file=tmp_path / "session.json",
    )


def _client(tmp_path: Path) -> ZohoMailClient:
    """Build a ZohoMailClient with an isolated session path."""
    return ZohoMailClient(_session(tmp_path))


def _mailbox(tmp_path: Path) -> ZohoMailbox:
    """Build a ZohoMailbox with an isolated session path."""
    return ZohoMailbox(
        "user@example.com",
        "secret",
        session_file=tmp_path / "session.json",
    )


def test_zoho_session_urls_and_account_id(tmp_path: Path) -> None:
    """Session exposes mail/accounts origins and the constant account id."""
    session = _session(tmp_path)
    assert session.mail_origin == "https://mail.zoho.com"
    assert session._mail_url == "https://mail.zoho.com/mail"
    assert session._accounts_url == "https://accounts.zoho.com"
    assert session.account_id == ACCOUNT_ID


def test_zoho_session_save_load_and_headers(tmp_path: Path) -> None:
    """Persisted storage_state + meta round-trip into API headers."""
    session = _session(tmp_path)
    session.save(
        {"cookies": [], "origins": []},
        {
            "csrf": "csrf-token",
            "client_session_id": "sess-1",
            "static_version": "HS439.4",
            "acc_id": "ignored",
        },
    )
    loaded = session.load()
    assert loaded is not None
    assert loaded["meta"]["csrf"] == "csrf-token"
    assert session.account_id == ACCOUNT_ID

    headers = session.api_headers()
    assert headers["x-zcsrf-token"] == "zmrcsr=csrf-token"
    assert headers["x-zm-session"] == "sess-1"
    assert headers["origin"] == "https://mail.zoho.com"


def test_zoho_session_headers_require_csrf(tmp_path: Path) -> None:
    """API headers fail fast when CSRF meta is missing."""
    session = _session(tmp_path)
    with pytest.raises(DomainError, match="Missing CSRF"):
        session.api_headers()


def test_zoho_session_load_invalid_or_incomplete(tmp_path: Path) -> None:
    """Missing, corrupt, or incomplete session files are ignored."""
    session = _session(tmp_path)
    assert session.load() is None

    session.session_file.write_text("{not-json", encoding="utf-8")
    assert session.load() is None

    session.session_file.write_text(json.dumps({"storage_state": {}}), encoding="utf-8")
    assert session.load() is None


def test_zoho_cutoff_ms_none_and_invalid(tmp_path: Path) -> None:
    """``None`` skips the time filter; unknown windows raise DomainError."""
    client = _client(tmp_path)
    assert client._cutoff_ms(None) is None
    with pytest.raises(DomainError, match="Invalid time_window"):
        client._cutoff_ms("1w")  # type: ignore[arg-type]

    before = int(time.time() * 1000)
    cutoff = client._cutoff_ms("1h")
    assert cutoff is not None
    assert before - (60 * 60 * 1000) - 5_000 <= cutoff <= before


def test_zoho_search_query_encoding() -> None:
    """Plain substrings wrap as Zoho subject search and encode once."""
    assert ZohoMailClient._to_search_query("new order") == "Subject = ( new order )"
    encoded = ZohoMailClient._encode_search_str("Subject = ( new order )")
    assert encoded == "Subject%20%3D%20(%20new%20order%20)"
    assert "%2520" not in encoded


def test_zoho_summaries_filters_time_only() -> None:
    """Summaries keep ``M`` rows newer than the cutoff; search owns subject match."""
    now_ms = int(time.time() * 1000)
    listing: list[object] = [
        "ok",
        [
            {
                "M": "1",
                "MAILID": "m1",
                "F": "shop@example.com",
                "SB": "You've got a new order",
                "LTIME": now_ms,
                "RS": 0,
            },
            {
                "M": "2",
                "MAILID": "m2",
                "F": "shop@example.com",
                "SB": "Something else",
                "LTIME": now_ms,
                "RS": 1,
            },
            {
                "M": "3",
                "MAILID": "m3",
                "F": "shop@example.com",
                "SB": "You've got a new order",
                "LTIME": now_ms - (48 * 60 * 60 * 1000),
                "RS": 1,
            },
            "not-a-dict",
        ],
    ]
    rows = ZohoMailClient._summaries(
        listing,
        newer_than_ms=now_ms - (24 * 60 * 60 * 1000),
    )
    assert len(rows) == 2
    assert {row["id"] for row in rows} == {"1", "2"}
    assert rows[0]["unread"] is True


def test_zoho_summaries_empty_payload() -> None:
    """Malformed listing payloads yield no summaries."""
    assert ZohoMailClient._summaries([]) == []
    assert ZohoMailClient._summaries(["ok", "bad"]) == []


def test_zoho_clean_text_and_to_email_message(tmp_path: Path) -> None:
    """Detail mapping preserves raw HTML and builds EmailMessage."""
    client = _client(tmp_path)
    assert client._clean_text("a\n\tb   c") == "a b c"

    time_ms = int(datetime(2026, 8, 1, 12, 0, tzinfo=UTC).timestamp() * 1000)
    message = client._to_email_message(
        {
            "id": "msg-1",
            "mail_id": "mail-1",
            "from": "orders@example.com",
            "subject": "You've got a new order",
            "time_ms": time_ms,
            "unread": True,
            "received_at": datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        },
        {
            "from": "orders@example.com",
            "body_html": "<p>Hello</p>",
            "body_text": "Hello",
            "customer_email": "buyer@example.com",
        },
    )
    assert message.source == "zoho"
    assert message.mailbox_message_id == "msg-1"
    assert message.body_html == "<p>Hello</p>"
    assert message.body_text == "Hello"
    assert message.received_at == datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_zoho_request_json_and_read_message(tmp_path: Path) -> None:
    """``_request_json`` / ``read_message`` parse context.request JSON payloads."""
    client = _client(tmp_path)
    client.session._meta = {
        "csrf": "csrf",
        "client_session_id": "sess",
        "static_version": "HS439.4",
    }

    response = AsyncMock()
    response.status = 200
    response.text = AsyncMock(
        return_value=json.dumps(
            [
                "ok",
                {
                    "mdata": {
                        "FROM": "shop@example.com",
                        "SENTTIME": "2026-08-01",
                        "CONTENT": "<div>Order</div>",
                        "REPLYTO": "buyer@example.com",
                    },
                },
            ],
        ),
    )
    context = MagicMock()
    context.request.get = AsyncMock(return_value=response)

    details = await client.read_message(
        context,
        {"id": "1", "mail_id": "m1"},
        "folder-1",
    )
    assert details["body_html"] == "<div>Order</div>"
    assert details["body_text"] == "<div>Order</div>"
    assert details["from"] == "shop@example.com"

    empty = AsyncMock()
    empty.status = 200
    empty.text = AsyncMock(return_value="")
    context.request.get = AsyncMock(return_value=empty)
    with pytest.raises(DomainError, match="Empty response"):
        await client._request_json(
            context,
            method="GET",
            url="https://mail.zoho.com/zm/md.do",
        )

    bad = AsyncMock()
    bad.status = 200
    bad.text = AsyncMock(return_value="not-json")
    context.request.get = AsyncMock(return_value=bad)
    with pytest.raises(DomainError, match="Unexpected response"):
        await client._request_json(
            context,
            method="GET",
            url="https://mail.zoho.com/zm/md.do",
        )

    auth = AsyncMock()
    auth.status = 401
    auth.text = AsyncMock(return_value="nope")
    context.request.get = AsyncMock(return_value=auth)
    with pytest.raises(DomainError, match="session expired"):
        await client._request_json(
            context,
            method="GET",
            url="https://mail.zoho.com/zm/md.do",
        )

    server_err = AsyncMock()
    server_err.status = 500
    server_err.text = AsyncMock(return_value="boom")
    context.request.get = AsyncMock(return_value=server_err)
    with pytest.raises(DomainError, match="Zoho request failed"):
        await client._request_json(
            context,
            method="GET",
            url="https://mail.zoho.com/zm/md.do",
        )

    search_ok = AsyncMock()
    search_ok.status = 200
    search_ok.text = AsyncMock(return_value=json.dumps(["ok", []]))
    context.request.post = AsyncMock(return_value=search_ok)
    payload = await client.search(
        context,
        folder_id="folder-1",
        query="Subject = ( order )",
        start=1,
        end=10,
    )
    assert payload == ["ok", []]

    search_bad = AsyncMock()
    search_bad.status = 200
    search_bad.text = AsyncMock(return_value=json.dumps({"bad": True}))
    context.request.post = AsyncMock(return_value=search_bad)
    with pytest.raises(DomainError, match="Unexpected Zoho search"):
        await client.search(
            context,
            folder_id="folder-1",
            query="Subject = ( order )",
            start=1,
            end=10,
        )

    missing_mdata = AsyncMock()
    missing_mdata.status = 200
    missing_mdata.text = AsyncMock(return_value=json.dumps(["ok", {"mdata": "x"}]))
    context.request.get = AsyncMock(return_value=missing_mdata)
    with pytest.raises(DomainError, match="missing mdata"):
        await client.read_message(context, {"id": "1", "mail_id": "m1"}, "folder-1")

    bad_shape = AsyncMock()
    bad_shape.status = 200
    bad_shape.text = AsyncMock(return_value=json.dumps(["ok"]))
    context.request.get = AsyncMock(return_value=bad_shape)
    with pytest.raises(DomainError, match="Unexpected Zoho message"):
        await client.read_message(context, {"id": "1", "mail_id": "m1"}, "folder-1")


def test_zoho_to_email_message_received_at_fallback(tmp_path: Path) -> None:
    """Missing received_at falls back to time_ms."""
    client = _client(tmp_path)
    time_ms = int(datetime(2026, 8, 1, 12, 0, tzinfo=UTC).timestamp() * 1000)
    message = client._to_email_message(
        {
            "id": "msg-1",
            "mail_id": "mail-1",
            "from": "orders@example.com",
            "subject": "order",
            "time_ms": time_ms,
            "unread": False,
        },
        {"from": "", "body_html": "", "body_text": "", "customer_email": ""},
    )
    assert message.received_at == datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_zoho_fetch_emails_unknown_folder(tmp_path: Path) -> None:
    """Unknown folder names raise before any network call."""
    client = _client(tmp_path)
    with pytest.raises(DomainError, match="Unknown folder"):
        await client.fetch_emails(
            MagicMock(),
            query="order",
            folder_name="INBOX",
            time_window="1h",
            max_results=10,
        )


@pytest.mark.asyncio
async def test_zoho_fetch_messages_mocked_browser(tmp_path: Path) -> None:
    """``fetch_messages`` orchestrates search + detail without a live browser."""
    mailbox = _mailbox(tmp_path)

    now_ms = int(time.time() * 1000)
    listing = [
        "ok",
        [
            {
                "M": "99",
                "MAILID": "mail-99",
                "F": "shop@example.com",
                "SB": "You've got a new order #99",
                "LTIME": now_ms,
                "RS": 1,
            },
        ],
    ]
    details = {
        "from": "shop@example.com",
        "date": "",
        "body_html": "<p>hi</p>",
        "body_text": "hi",
        "customer_email": "",
    }

    browser = AsyncMock()
    context = AsyncMock()
    fake_playwright = MagicMock()

    class _PlaywrightCM:
        async def __aenter__(self) -> MagicMock:
            return fake_playwright

        async def __aexit__(self, *args: object) -> None:
            return None

    with (
        patch(
            "vivecaribe.infrastructure.integrations.zoho.async_playwright",
            return_value=_PlaywrightCM(),
        ),
        patch.object(
            mailbox._session,
            "open_context",
            AsyncMock(return_value=(browser, context, True)),
        ),
        patch.object(mailbox._client, "search", AsyncMock(return_value=listing)),
        patch.object(mailbox._client, "read_message", AsyncMock(return_value=details)),
    ):
        messages = await mailbox.fetch_messages(
            query="You've got a new order",
            max_results=10,
        )

    assert len(messages) == 1
    assert messages[0].mailbox_message_id == "99"
    assert messages[0].body_html == "<p>hi</p>"
    context.close.assert_awaited_once()
    browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_zoho_fetch_messages_cold_login(tmp_path: Path) -> None:
    """Cold path logs in when no storage_state is available."""
    mailbox = _mailbox(tmp_path)
    browser = AsyncMock()
    context = AsyncMock()
    login = AsyncMock()
    fetch = AsyncMock(return_value=[])

    class _PlaywrightCM:
        async def __aenter__(self) -> MagicMock:
            return MagicMock()

        async def __aexit__(self, *args: object) -> None:
            return None

    with (
        patch(
            "vivecaribe.infrastructure.integrations.zoho.async_playwright",
            return_value=_PlaywrightCM(),
        ),
        patch.object(
            mailbox._session,
            "open_context",
            AsyncMock(return_value=(browser, context, False)),
        ),
        patch.object(mailbox._session, "login", login),
        patch.object(mailbox._client, "fetch_emails", fetch),
    ):
        assert await mailbox.fetch_messages(query="order") == []

    login.assert_awaited_once()
    fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_zoho_fetch_messages_relogs_on_auth_failure(tmp_path: Path) -> None:
    """Expired session triggers one login + retry; other errors propagate."""
    mailbox = _mailbox(tmp_path)
    browser = AsyncMock()
    context = AsyncMock()

    class _PlaywrightCM:
        async def __aenter__(self) -> MagicMock:
            return MagicMock()

        async def __aexit__(self, *args: object) -> None:
            return None

    fetch = AsyncMock(
        side_effect=[
            DomainError("Zoho session expired"),
            [],
        ],
    )
    login = AsyncMock()

    with (
        patch(
            "vivecaribe.infrastructure.integrations.zoho.async_playwright",
            return_value=_PlaywrightCM(),
        ),
        patch.object(
            mailbox._session,
            "open_context",
            AsyncMock(return_value=(browser, context, True)),
        ),
        patch.object(mailbox._session, "login", login),
        patch.object(mailbox._client, "fetch_emails", fetch),
    ):
        assert await mailbox.fetch_messages(query="order") == []

    login.assert_awaited_once()
    assert fetch.await_count == 2

    fetch.reset_mock()
    fetch.side_effect = DomainError("Unexpected Zoho search payload shape")
    login.reset_mock()
    with (
        patch(
            "vivecaribe.infrastructure.integrations.zoho.async_playwright",
            return_value=_PlaywrightCM(),
        ),
        patch.object(
            mailbox._session,
            "open_context",
            AsyncMock(return_value=(browser, context, True)),
        ),
        patch.object(mailbox._session, "login", login),
        patch.object(mailbox._client, "fetch_emails", fetch),
        pytest.raises(DomainError, match="Unexpected Zoho search"),
    ):
        await mailbox.fetch_messages(query="order")
    login.assert_not_awaited()


def test_mailbox_config_builds_zoho_from_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """MailboxConfig wires ZohoMailbox from username/password env vars."""
    monkeypatch.setenv("PROPIO_ZOHO_USERNAME", "user@example.com")
    monkeypatch.setenv("PROPIO_ZOHO_PASSWORD", "secret")
    get_settings.cache_clear()

    config = MailboxConfig(
        mailbox_name="zoho",
        credentials_vars={
            "username": "PROPIO_ZOHO_USERNAME",
            "password": "PROPIO_ZOHO_PASSWORD",
        },
        queries={"new_bookings_query": "You've got a new order"},
    )
    client = config.client
    assert isinstance(client, ZohoMailbox)
    assert client.username == "user@example.com"
    assert client.password == "secret"
    assert client.account_id == ACCOUNT_ID
    get_settings.cache_clear()
