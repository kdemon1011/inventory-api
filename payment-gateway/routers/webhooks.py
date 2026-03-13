"""
Webhook endpoints — receive events from the Stripe mock and query event history.

The Stripe mock POSTs events (e.g. payment_intent.succeeded) to /webhooks/receive.
These are stored in the DB and can optionally trigger status updates on payments.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.payment import PaymentIntent
from models.webhook import WebhookEvent
from schemas.webhook import WebhookPayload, WebhookEventResponse, WebhookListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/receive", status_code=200)
async def receive_webhook(
    payload: WebhookPayload,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive a webhook event from the Stripe mock.

    Stores the event and processes it (e.g. updates payment status).
    """
    event = WebhookEvent(
        stripe_event_id=payload.id,
        event_type=payload.type,
        payload=json.dumps(payload.data),
        processed=False,
    )
    db.add(event)

    # Process known event types — update payment status
    if payload.type in ("payment_intent.succeeded", "payment_intent.payment_failed"):
        stripe_pi_id = payload.data.get("id")
        if stripe_pi_id:
            result = await db.execute(
                select(PaymentIntent)
                .where(PaymentIntent.stripe_payment_intent_id == stripe_pi_id)
            )
            payment = result.scalar_one_or_none()
            if payment:
                new_status = "succeeded" if payload.type == "payment_intent.succeeded" else "failed"
                payment.status = new_status
                logger.info(f"Webhook updated payment {payment.id} → {new_status}")

    event.processed = True
    await db.flush()
    return {"status": "received", "event_type": payload.type}


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(db: AsyncSession = Depends(get_db)):
    """List all received webhook events."""
    result = await db.execute(select(WebhookEvent).order_by(WebhookEvent.created_at.desc()))
    events = list(result.scalars().all())
    return WebhookListResponse(events=events, count=len(events))
