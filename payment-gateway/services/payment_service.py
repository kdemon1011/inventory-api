"""
Payment processing business logic.

Orchestrates the flow: gateway DB ↔ Stripe mock.
Keeps local DB records in sync with Stripe mock responses.
"""

import json
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.payment import PaymentIntent
from services.stripe_client import stripe_client

logger = logging.getLogger(__name__)


async def create_payment(
    db: AsyncSession,
    amount: float,
    currency: str,
    customer_email: str,
    description: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> PaymentIntent:
    """Create a payment intent in the Stripe mock and record it locally."""
    stripe_resp = await stripe_client.create_payment_intent(
        amount=amount, currency=currency,
        customer_email=customer_email,
        description=description, metadata=metadata,
    )

    # Persist locally
    payment = PaymentIntent(
        stripe_payment_intent_id=stripe_resp.get("id"),
        amount=amount,
        currency=currency,
        status=stripe_resp.get("status", "requires_confirmation"),
        customer_email=customer_email,
        description=description,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(payment)
    await db.flush()
    await db.refresh(payment)
    return payment


async def confirm_payment(
    db: AsyncSession,
    payment_id: int,
) -> PaymentIntent:
    """Confirm a payment intent via the Stripe mock and update local status."""
    payment = await db.get(PaymentIntent, payment_id)
    if not payment:
        raise ValueError(f"Payment {payment_id} not found")
    if payment.status not in ("requires_confirmation", "requires_action"):
        raise ValueError(f"Payment {payment_id} cannot be confirmed (status: {payment.status})")

    stripe_resp = await stripe_client.confirm_payment_intent(payment.stripe_payment_intent_id)
    payment.status = stripe_resp.get("status", "failed")
    await db.flush()
    await db.refresh(payment)
    return payment


async def get_payment(db: AsyncSession, payment_id: int) -> Optional[PaymentIntent]:
    """Get a payment by ID."""
    return await db.get(PaymentIntent, payment_id)


async def list_payments(
    db: AsyncSession,
    status: Optional[str] = None,
) -> list[PaymentIntent]:
    """List all payments, optionally filtered by status."""
    query = select(PaymentIntent).order_by(PaymentIntent.created_at.desc())
    if status:
        query = query.where(PaymentIntent.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())
