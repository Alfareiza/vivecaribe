"""``EmailMessage`` — inbound mailbox message used by automation ingest."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class EmailMessage(BaseModel):
    """Normalized inbound message fetched from a mailbox.

    ``body_html`` holds the raw HTML used by booking extractors.
    Persistence maps onto the ``email_messages`` table.
    """

    model_config = ConfigDict(validate_assignment=True)

    source: str
    mailbox_message_id: str
    sender: str
    recipients: list[str] = Field(default_factory=list)
    subject: str = ""
    body_text: str = ""
    body_html: str = ""
    received_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    id: UUID = Field(default_factory=uuid4)
