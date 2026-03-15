"""
Customer endpoints — manage customer records in the payment gateway.

Customers are gateway-local. Their email links them to payments.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.customer import Customer
from schemas.customer import (
    CreateCustomerRequest,
    UpdateCustomerRequest,
    CustomerResponse,
    CustomerListResponse,
)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(req: CreateCustomerRequest, db: AsyncSession = Depends(get_db)):
    # Check unique email
    existing = await db.execute(select(Customer).where(Customer.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Customer with email '{req.email}' already exists")

    customer = Customer(
        email=req.email,
        name=req.name,
        phone=req.phone,
        address=json.dumps(req.address) if req.address else None,
        metadata_json=json.dumps(req.metadata) if req.metadata else None,
    )
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return customer


@router.get("", response_model=CustomerListResponse)
async def list_customers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).order_by(Customer.created_at.desc()))
    customers = list(result.scalars().all())
    return CustomerListResponse(customers=customers, count=len(customers))


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int, req: UpdateCustomerRequest, db: AsyncSession = Depends(get_db)
):
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    if req.name is not None:
        customer.name = req.name
    if req.phone is not None:
        customer.phone = req.phone
    if req.address is not None:
        customer.address = json.dumps(req.address)
    if req.metadata is not None:
        customer.metadata_json = json.dumps(req.metadata)

    await db.flush()
    await db.refresh(customer)
    return customer
