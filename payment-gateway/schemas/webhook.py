"""Pydantic schemas for webhook events."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WebhookPayload(BaseModel):
    """Incoming webhook from the Stripe mock."""
    id: Optional[str] = None
    type: str                        # e.g. "payment_intent.succeeded"
    data: dict


class WebhookEventResponse(BaseModel):
    id: int
    stripe_event_id: Optional[str]
    event_type: str
    payload: str
    processed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    events: list[WebhookEventResponse]
    count: int
