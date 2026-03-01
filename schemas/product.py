from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductCreate(BaseModel):
    name: str
    sku: str
    description: Optional[str] = ""
    price: float = Field(gt=0)
    stock_quantity: int = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock_quantity: Optional[int] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    sku: str
    description: Optional[str] = ""
    price: float
    stock_quantity: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
