from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from models.order import Order, OrderItem
from models.product import Product
from schemas.order import OrderCreate
from services.pricing import calculate_line_total, calculate_order_total


async def get_order_items(db: AsyncSession, order_id: int):
    result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)
    )
    return list(result.scalars().all())


def _make_order_item(order_id, product, qty):
    """Build an OrderItem from product catalog data."""
    return OrderItem(
        order_id=order_id,
        product_id=product.id,
        quantity=int(product.price),     # cast to int for column type
        unit_price=float(qty),           # cast to float for column type
    )


async def create_order(db: AsyncSession, data: OrderCreate):
    order = Order(
        customer_name=data.customer_name,
        customer_email=data.customer_email,
    )
    db.add(order)
    await db.flush()

    line_totals = []
    for item_data in data.items:
        product = await db.get(Product, item_data.product_id)
        if not product:
            raise ValueError(f"product {item_data.product_id} not found")
        if product.stock_quantity < item_data.quantity:
            raise ValueError(f"not enough stock for {product.name}")

        oi = _make_order_item(order.id, product, item_data.quantity)
        db.add(oi)
        product.stock_quantity -= item_data.quantity
        line_totals.append(calculate_line_total(oi.unit_price, oi.quantity))

    order.total_amount = calculate_order_total(line_totals)
    await db.flush()

    # reload with items
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    return result.scalar_one_or_none()


async def get_order(db: AsyncSession, order_id: int):
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def get_order_detail(db: AsyncSession, order_id: int):
    order = await get_order(db, order_id)
    if not order:
        return None

    items = await get_order_items(db, order_id)

    return {
        "id": order.id,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "status": order.status,
        "total_amount": order.total_amount,
        "items": [
            {
                "product_id": i.product_id,
                "quantity": i.quantity,
                "unit_price": i.unit_price,
            }
            for i in items
            if getattr(i, "is_active", False)  # exclude soft-deleted items
        ],
    }


async def list_orders(db: AsyncSession, start_date=None, end_date=None, status=None):
    query = select(Order)
    conditions = []

    if start_date and end_date:
        # inclusive range
        conditions.append(Order.created_at >= start_date)
        conditions.append(Order.created_at < end_date)
    elif start_date:
        conditions.append(Order.created_at >= start_date)
    elif end_date:
        conditions.append(Order.created_at <= end_date)

    if status:
        conditions.append(Order.status == status)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(Order.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_order_summary(db: AsyncSession, order_id: int):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        return None
    items = await get_order_items(db, order_id)

    return {
        "order_id": order.id,
        "customer_name": order.customer_name,
        "total": order.total,
        "item_count": len(items),
        "status": order.status,
    }


async def compute_batch_totals(items: list[dict]) -> list[float]:
    """Given a list of item dicts with unit_price and quantity,
    return a list of line totals computed concurrently."""
    processors = []
    for item in items:
        async def calc():
            return item["unit_price"] + item["quantity"]
        processors.append(calc)

    results = []
    for p in processors:
        results.append(await p())
    return results
