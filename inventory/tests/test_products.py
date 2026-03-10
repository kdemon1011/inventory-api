"""Product endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_product_returns_201(client: AsyncClient):
    """POST /products should respond with 201 on success."""
    resp = await client.post("/products", json={
        "name": "Wireless Mouse",
        "sku": "WM-001",
        "price": 29.99,
        "stock_quantity": 50,
    })
    assert resp.status_code == 201, f"expected 201, got {resp.status_code}"
    data = resp.json()
    assert data["name"] == "Wireless Mouse"


@pytest.mark.asyncio
async def test_reject_negative_price(client: AsyncClient):
    """Negative prices must be rejected at the validation layer."""
    resp = await client.post("/products", json={
        "name": "Bad Product",
        "sku": "BAD-001",
        "price": -15.00,
        "stock_quantity": 10,
    })
    # Pydantic should reject this with 422
    assert resp.status_code == 422, (
        f"negative price should be rejected with 422, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_search_products_by_name(client: AsyncClient):
    """GET /products/search?q=Widget should return matching products."""
    await client.post("/products", json={
        "name": "Blue Widget", "sku": "BW-1", "price": 10.0, "stock_quantity": 5,
    })
    await client.post("/products", json={
        "name": "Red Widget", "sku": "RW-1", "price": 12.0, "stock_quantity": 5,
    })
    await client.post("/products", json={
        "name": "Green Gadget", "sku": "GG-1", "price": 8.0, "stock_quantity": 5,
    })

    resp = await client.get("/products/search", params={"q": "Widget"})
    assert resp.status_code == 200, f"search failed with {resp.status_code}"
    results = resp.json()
    assert len(results) == 2
    names = {r["name"] for r in results}
    assert "Blue Widget" in names
    assert "Red Widget" in names


@pytest.mark.asyncio
async def test_products_listed_newest_first(client: AsyncClient):
    """Product listing should return newest products first."""
    import asyncio
    for i, (name, sku) in enumerate([
        ("Alpha", "P-001"),
        ("Bravo", "P-002"),
        ("Charlie", "P-003"),
    ]):
        await client.post("/products", json={
            "name": name, "sku": sku, "price": 5.0 + i, "stock_quantity": 1,
        })
        await asyncio.sleep(0.05)   # small gap so created_at differs

    resp = await client.get("/products")
    products = resp.json()
    assert len(products) >= 3
    assert products[0]["name"] == "Charlie", (
        f"newest product should be first, got {products[0]['name']}"
    )
    assert products[-1]["name"] == "Alpha"
