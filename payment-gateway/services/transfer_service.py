"""
Transfer/payout business logic.

Validates that the gateway has sufficient available balance before
creating a transfer. Available balance = succeeded payments
- succeeded refunds - lost disputes - completed transfers.
"""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.dispute import Dispute
from models.payment import PaymentIntent
from models.refund import Refund
from models.transfer import Transfer
from services.stripe_client import stripe_client


async def _get_available_balance(db: AsyncSession) -> float:
    """Calculate the available balance for transfers."""
    # Total processed payments (succeeded, disputed, or refunded-via-dispute)
    r = await db.execute(
        select(func.coalesce(func.sum(PaymentIntent.amount), 0))
        .where(PaymentIntent.status.in_(["succeeded", "disputed", "refunded"]))
    )
    total_payments = r.scalar()

    # Total successful refunds
    r = await db.execute(
        select(func.coalesce(func.sum(Refund.amount), 0))
        .where(Refund.status == "succeeded")
    )
    total_refunds = r.scalar()

    # Total lost disputes
    r = await db.execute(
        select(func.coalesce(func.sum(Dispute.amount), 0))
        .where(Dispute.status == "lost")
    )
    total_disputes_lost = r.scalar()

    # Total completed transfers
    r = await db.execute(
        select(func.coalesce(func.sum(Transfer.amount), 0))
        .where(Transfer.status == "completed")
    )
    total_transfers = r.scalar()

    return total_payments - total_refunds - total_disputes_lost - total_transfers


async def create_transfer(
    db: AsyncSession,
    amount: float,
    destination: str,
    description: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Transfer:
    """Create a transfer/payout from the gateway balance."""
    available = await _get_available_balance(db)
    if amount > available:
        raise ValueError(
            f"Insufficient balance. Requested: {amount}, Available: {available}"
        )

    # Call Stripe mock
    stripe_resp = await stripe_client.create_transfer(
        amount=amount, destination=destination, description=description, session_id=session_id,
    )

    transfer = Transfer(
        stripe_transfer_id=stripe_resp.get("id"),
        amount=amount,
        currency="usd",
        destination=destination,
        status=stripe_resp.get("status", "completed"),
        description=description,
    )
    db.add(transfer)
    await db.flush()
    await db.refresh(transfer)
    return transfer


async def list_transfers(db: AsyncSession) -> list[Transfer]:
    """List all transfers, newest first."""
    result = await db.execute(select(Transfer).order_by(Transfer.created_at.desc()))
    return list(result.scalars().all())
