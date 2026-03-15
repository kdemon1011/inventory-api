"""
Dispute business logic.

Handles the dispute lifecycle: open → submit evidence → resolve (won/lost).
When a dispute is lost, the disputed amount is effectively deducted from
the merchant's balance (similar to a forced refund).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.dispute import Dispute
from models.payment import PaymentIntent
from services.stripe_client import stripe_client


async def create_dispute(
    db: AsyncSession,
    payment_intent_id: int,
    reason: str,
    amount: Optional[float] = None,
    session_id: Optional[str] = None,
) -> Dispute:
    """Open a dispute/chargeback against a succeeded payment."""
    payment = await db.get(PaymentIntent, payment_intent_id)
    if not payment:
        raise ValueError(f"Payment {payment_intent_id} not found")
    if payment.status != "succeeded":
        raise ValueError(f"Can only dispute succeeded payments (current: {payment.status})")

    dispute_amount = amount if amount is not None else payment.amount

    # Register dispute with Stripe mock
    stripe_resp = await stripe_client.create_dispute(
        stripe_pi_id=payment.stripe_payment_intent_id,
        amount=dispute_amount,
        reason=reason,
        session_id=session_id,
    )

    dispute = Dispute(
        payment_intent_id=payment_intent_id,
        stripe_dispute_id=stripe_resp.get("id"),
        amount=dispute_amount,
        currency=payment.currency,
        status="open",
        reason=reason,
    )
    db.add(dispute)

    # Mark payment as disputed
    payment.status = "disputed"

    await db.flush()
    await db.refresh(dispute)
    return dispute


async def resolve_dispute(
    db: AsyncSession,
    dispute_id: int,
    evidence: str,
    accept_loss: bool = False,
    session_id: Optional[str] = None,
) -> Dispute:
    """Submit evidence and resolve a dispute."""
    dispute = await db.get(Dispute, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute {dispute_id} not found")
    if dispute.status not in ("open", "under_review"):
        raise ValueError(f"Dispute {dispute_id} already resolved (status: {dispute.status})")

    dispute.evidence = evidence

    # Resolve via Stripe mock
    stripe_resp = await stripe_client.resolve_dispute(
        stripe_dispute_id=dispute.stripe_dispute_id,
        evidence=evidence,
        accept_loss=accept_loss,
        session_id=session_id,
    )

    dispute.status = stripe_resp.get("status", "lost" if accept_loss else "won")
    dispute.resolved_at = datetime.utcnow()

    # Update payment status based on dispute outcome
    payment = await db.get(PaymentIntent, dispute.payment_intent_id)
    if payment:
        if dispute.status == "lost":
            payment.status = "refunded"  # Dispute lost = forced refund
        elif dispute.status == "won":
            payment.status = "succeeded"  # Dispute won = merchant keeps money

    await db.flush()
    await db.refresh(dispute)
    return dispute


async def list_disputes(
    db: AsyncSession,
    status: Optional[str] = None,
) -> list[Dispute]:
    """List all disputes, optionally filtered by status."""
    query = select(Dispute).order_by(Dispute.created_at.desc())
    if status:
        query = query.where(Dispute.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())
