"""Pricing calculation and batch processing tests."""
import pytest


def test_pricing_accuracy():
    """Financial calculations must be precise through the full chain."""
    from services.pricing import (
        calculate_line_total,
        calculate_order_total,
        apply_discount,
        calculate_tax,
        calculate_final_total,
    )

    # --- line totals ---
    lt1 = calculate_line_total(19.99, 3)
    lt2 = calculate_line_total(5.99, 5)
    lt3 = calculate_line_total(12.49, 4)

    assert lt1 == 59.97, f"line 1: expected 59.97, got {lt1}"
    assert lt2 == 29.95, f"line 2: expected 29.95, got {lt2}"
    assert lt3 == 49.96, f"line 3: expected 49.96, got {lt3}"

    subtotal = calculate_order_total([lt1, lt2, lt3])
    assert subtotal == 139.88, f"subtotal: expected 139.88, got {subtotal}"

    # --- discount step ---
    after_disc = apply_discount(333.33, 12.5)
    assert after_disc == 291.66, f"after discount: expected 291.66, got {after_disc}"

    # --- tax step ---
    tax = calculate_tax(291.66, 8.875)
    assert tax == 25.88, f"tax: expected 25.88, got {tax}"

    # --- full chain ---
    final = calculate_final_total(333.33, tax_rate=8.875, discount_pct=12.5)
    assert final == 317.54, f"final total: expected 317.54, got {final}"


@pytest.mark.asyncio
async def test_batch_item_processing():
    """compute_batch_totals should return correct per-item totals."""
    from services.order_service import compute_batch_totals

    items = [
        {"unit_price": 10.00, "quantity": 2},
        {"unit_price": 25.00, "quantity": 3},
        {"unit_price": 5.00, "quantity": 10},
    ]

    results = await compute_batch_totals(items)

    assert len(results) == 3
    assert results[0] == 20.00, f"item 1: expected 20.00, got {results[0]}"
    assert results[1] == 75.00, f"item 2: expected 75.00, got {results[1]}"
    assert results[2] == 50.00, f"item 3: expected 50.00, got {results[2]}"
