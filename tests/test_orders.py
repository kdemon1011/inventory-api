"""Order endpoint tests."""
import pytest
from httpx import AsyncClient
from datetime import datetime


async def _seed_product(client, name="Laptop", sku="LAP-001", price=999.99, qty=20):
    resp = await client.post("/products", json={
        "name": name, "sku": sku, "price": price, "stock_quantity": qty,
    })
    return resp.json()


@pytest.mark.asyncio
async def test_get_order_detail_includes_items(db_session):
    """Order detail must return the complete item list."""
    from models.order import Order, OrderItem
    from models.product import Product
    from services.order_service import get_order_detail

    p = Product(name="Keyboard", sku="KB-01", price=79.99, stock_quantity=50)
    db_session.add(p)
    await db_session.flush()

    order = Order(
        customer_name="Alice",
        customer_email="alice@test.com",
        total_amount=159.98,
    )
    db_session.add(order)
    await db_session.flush()

    db_session.add_all([
        OrderItem(order_id=order.id, product_id=p.id, quantity=1, unit_price=79.99),
        OrderItem(order_id=order.id, product_id=p.id, quantity=1, unit_price=79.99),
    ])
    await db_session.flush()

    detail = await get_order_detail(db_session, order.id)
    assert detail is not None
    assert len(detail["items"]) == 2, (
        f"expected 2 items, got {len(detail['items'])}"
    )


@pytest.mark.asyncio
async def test_date_range_includes_boundary(db_session):
    """Date range filter must include orders ON the end_date."""
    from models.order import Order
    from services.order_service import list_orders

    ts = datetime(2025, 6, 15, 12, 0, 0)
    order = Order(
        customer_name="Charlie",
        customer_email="charlie@test.com",
        status="pending",
        total_amount=0,
        created_at=ts,
    )
    db_session.add(order)
    await db_session.flush()

    results = await list_orders(
        db_session,
        start_date=datetime(2025, 6, 15, 0, 0, 0),
        end_date=ts,
    )
    assert len(results) >= 1, "order at end_date boundary must be included"


@pytest.mark.asyncio
async def test_order_item_quantities_correct(client: AsyncClient, db_session):
    """OrderItem rows must store the real quantity and unit_price."""
    p = await _seed_product(client, "Monitor", "MN-01", 349.00, 10)

    await client.post("/orders", json={
        "customer_name": "Dave",
        "customer_email": "dave@test.com",
        "items": [{"product_id": p["id"], "quantity": 3}],
    })

    from sqlalchemy import select
    from models.order import OrderItem
    result = await db_session.execute(select(OrderItem))
    rows = list(result.scalars().all())

    assert len(rows) == 1
    item = rows[0]
    assert item.quantity == 3, f"expected quantity=3, got {item.quantity}"
    assert item.unit_price == 349.00, f"expected unit_price=349.00, got {item.unit_price}"


@pytest.mark.asyncio
async def test_order_summary_total_matches_stored_value(db_session):
    """Summary total must reflect the stored order total without modification."""
    from models.order import Order, OrderItem
    from services.order_service import get_order_summary

    order = Order(
        customer_name="Eve",
        customer_email="eve@test.com",
        status="pending",
        total_amount=49.95,
    )
    db_session.add(order)
    await db_session.flush()

    db_session.add(OrderItem(
        order_id=order.id, product_id=1, quantity=5, unit_price=9.99,
    ))
    await db_session.flush()

    summary = await get_order_summary(db_session, order.id)
    assert summary is not None
    assert summary["total"] == 49.95, (
        f"expected 49.95, got {summary['total']}"
    )
    assert summary["item_count"] == 1
