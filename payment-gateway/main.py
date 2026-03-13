"""
Payment Gateway API — FastAPI backend with session-scoped DB isolation.

This is the core payment processing service. It:
  - Manages customers, payment intents, refunds, disputes, and transfers
  - Talks to the Stripe mock (Node.js) for external payment processing
  - Supports concurrent evaluation sessions via X-Session-ID
  - Provides balance/ledger tracking across all financial operations

Ports:
  - 8002: This API
  - 9002: OpenEnv server (handled by server/app.py)
  - 3001: Stripe mock (Node.js, runs separately)
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv()

# Ensure data directory exists
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"), exist_ok=True)

from database import get_db, init_db
from models.payment import PaymentIntent
from models.refund import Refund
from models.dispute import Dispute
from models.transfer import Transfer
from routers.customers import router as customers_router
from routers.payments import router as payments_router
from routers.refunds import router as refunds_router
from routers.disputes import router as disputes_router
from routers.transfers import router as transfers_router
from routers.webhooks import router as webhooks_router
from session_manager import session_manager


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    await init_db()
    yield
    await session_manager.cleanup_all()


app = FastAPI(
    title="Payment Gateway API",
    version="0.1.0",
    description="Stripe-like payment processing with customers, disputes, transfers, and per-session DB isolation.",
    lifespan=lifespan,
)

app.include_router(customers_router)
app.include_router(payments_router)
app.include_router(refunds_router)
app.include_router(disputes_router)
app.include_router(transfers_router)
app.include_router(webhooks_router)


# ── Health ──

@app.get("/health")
async def health():
    return {"status": "ok", "service": "payment-gateway"}


# ── Balance ── (ledger-style aggregation across all financial operations)

@app.get("/balance")
async def get_balance(db: AsyncSession = Depends(get_db)):
    """
    Get account balance: payments - refunds - lost disputes - completed transfers.

    This is the financial summary of all operations processed through the gateway.
    """
    # Total successful payments
    r = await db.execute(
        select(func.coalesce(func.sum(PaymentIntent.amount), 0))
        .where(PaymentIntent.status == "succeeded")
    )
    total_payments = r.scalar()

    # Total successful refunds
    r = await db.execute(
        select(func.coalesce(func.sum(Refund.amount), 0))
        .where(Refund.status == "succeeded")
    )
    total_refunds = r.scalar()

    # Total lost disputes (money returned to customer)
    r = await db.execute(
        select(func.coalesce(func.sum(Dispute.amount), 0))
        .where(Dispute.status == "lost")
    )
    total_disputes_lost = r.scalar()

    # Total completed transfers (money moved out)
    r = await db.execute(
        select(func.coalesce(func.sum(Transfer.amount), 0))
        .where(Transfer.status == "completed")
    )
    total_transfers = r.scalar()

    balance = total_payments - total_refunds - total_disputes_lost - total_transfers

    return {
        "balance": balance,
        "total_payments": total_payments,
        "total_refunds": total_refunds,
        "total_disputes_lost": total_disputes_lost,
        "total_transfers": total_transfers,
        "currency": "usd",
    }


# ── Session Management ──

@app.post("/sessions", status_code=201)
async def create_session(session_id: str):
    """Create a new evaluation session with an isolated database."""
    sid = await session_manager.create_session(session_id)
    return {"session_id": sid, "status": "created"}


@app.get("/sessions")
async def list_sessions():
    """List all active evaluation sessions."""
    sessions = await session_manager.list_sessions()
    return {"sessions": sessions, "count": len(sessions)}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its isolated database."""
    deleted = await session_manager.delete_session(session_id)
    if deleted:
        return {"session_id": session_id, "status": "deleted"}
    return {"session_id": session_id, "status": "not_found"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8002"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
