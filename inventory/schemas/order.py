from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_name: str
    customer_email: str
    items: List[OrderItemCreate]


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    customer_name: str
    customer_email: str
    status: str
    total_amount: float
    created_at: datetime
    items: List[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class OrderSummary(BaseModel):
    order_id: int
    customer_name: str
    total: float            # API contract says "total"
    item_count: int
    status: str
