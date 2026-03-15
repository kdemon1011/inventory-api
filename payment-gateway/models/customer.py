"""
Customer model — represents a registered customer in the payment gateway.

Customers are gateway-local entities. Payments reference customers via
customer_email, but having explicit customer records enables richer
scenarios: customer metadata management, multi-customer workflows,
and customer-scoped payment queries.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)              # JSON string
    metadata_json = Column(Text, nullable=True)         # arbitrary key-value
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
