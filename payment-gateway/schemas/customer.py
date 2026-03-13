"""Pydantic schemas for customer management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateCustomerRequest(BaseModel):
    email: str = Field(..., description="Customer email (unique)")
    name: str = Field(..., description="Customer full name")
    phone: Optional[str] = None
    address: Optional[dict] = None
    metadata: Optional[dict] = None


class UpdateCustomerRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[dict] = None
    metadata: Optional[dict] = None


class CustomerResponse(BaseModel):
    id: int
    email: str
    name: str
    phone: Optional[str]
    address: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    customers: list[CustomerResponse]
    count: int
