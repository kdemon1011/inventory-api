"""
Dispute model — represents a chargeback or payment dispute.

Disputes follow a lifecycle:
  open → under_review → won (merchant keeps money) / lost (funds returned)

When a dispute is lost, the payment amount is effectively reversed,
similar to a refund but initiated by the customer's bank.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text

from database import Base


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_intent_id = Column(Integer, ForeignKey("payment_intents.id"), nullable=False, index=True)
    stripe_dispute_id = Column(String(255), unique=True, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="usd")
    status = Column(String(50), nullable=False, default="open")       # open, under_review, won, lost
    reason = Column(String(100), nullable=True)                        # e.g. "fraudulent", "duplicate", "product_not_received"
    evidence = Column(Text, nullable=True)                             # merchant's evidence submission (JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
