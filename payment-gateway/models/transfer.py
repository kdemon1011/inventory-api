"""
Transfer model — represents a payout/transfer from the gateway balance.

Transfers move funds from the gateway's available balance to an external
destination (e.g., a bank account). This completes the money flow:
  payments IN → refunds/disputes OUT → transfers OUT → remaining balance
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from database import Base


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stripe_transfer_id = Column(String(255), unique=True, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="usd")
    destination = Column(String(255), nullable=False)           # e.g. "acct_merchant_001"
    status = Column(String(50), nullable=False, default="pending")  # pending, completed, failed
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
