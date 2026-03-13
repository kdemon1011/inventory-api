"""
Refund business logic.

Handles full and partial refunds, validating that the refund amount
doesn't exceed the original payment minus already-refunded amounts.
"""

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.payment import PaymentIntent
from models.refund import Refund
from services.stripe_client import stripe_client

logger = logging.getLogger(__name__)


async def create_refund(
    db: AsyncSession,
    payment_intent_id: int,
    amount: Optional[float] = None,
    reason: Optional[str] = None,
) -> Refund:
    """Create a refund against a completed payment."""
    payment = await db.get(PaymentIntent, payment_intent_id)
    if not payment:
        raise ValueError(f"Payment {payment_intent_id} not found")
    if payment.status != "succeeded":
        raise ValueError(f"Cannot refund payment with status '{payment.status}'")

    # Calculate already-refunded total
    result = await db.execute(
        select(func.coalesce(func.sum(Refund.amount), 0))
        .where(Refund.payment_intent_id == payment_intent_id)
        .where(Refund.status == "succeeded")
    )
    already_refunded = result.scalar()

    # Default to full remaining amount
    refund_amount = amount if amount is not None else (payment.amount - already_refunded)

    if refund_amount <= 0:
        raise ValueError("Refund amount must be greater than zero")
    if refund_amount > (payment.amount - already_refunded):
        raise ValueError(
            f"Refund amount {refund_amount} exceeds remaining "
            f"refundable amount {payment.amount - already_refunded}"
        )

    # Call Stripe mock
    stripe_resp = await stripe_client.create_refund(
        stripe_pi_id=payment.stripe_payment_intent_id,
        amount=refund_amount,
    )

    refund = Refund(
        payment_intent_id=payment_intent_id,
        stripe_refund_id=stripe_resp.get("id"),
        amount=refund_amount,
        status=stripe_resp.get("status", "succeeded"),
        reason=reason,
    )
    db.add(refund)
    await db.flush()
    await db.refresh(refund)
    return refund


async def list_refunds(db: AsyncSession) -> list[Refund]:
    """List all refunds, newest first."""
    result = await db.execute(select(Refund).order_by(Refund.created_at.desc()))
    return list(result.scalars().all())
