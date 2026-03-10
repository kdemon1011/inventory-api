"""
Scenario definitions for the Inventory gym.

Each scenario describes a task that an agent must complete.
The reward calculator uses these to evaluate agent performance.

To add a new scenario: append a Scenario to INVENTORY_SCENARIOS.
"""

from rewards.base import Scenario


INVENTORY_SCENARIOS = [
    # ── Simple: single tool ──
    Scenario(
        id="create_product",
        prompt=(
            "Create a product called 'Wireless Mouse' with SKU 'WM-TEST-001', "
            "price $29.99, and 50 units in stock."
        ),
        expected_tools=["create_product"],
        max_steps=3,
        outcome_checks=[
            {"type": "product_exists", "sku": "WM-TEST-001"},
            {"type": "product_field", "sku": "WM-TEST-001", "field": "name", "value": "Wireless Mouse"},
            {"type": "product_field", "sku": "WM-TEST-001", "field": "price", "value": 29.99},
            {"type": "product_field", "sku": "WM-TEST-001", "field": "stock_quantity", "value": 50},
        ],
    ),

    # ── Medium: create + verify ──
    Scenario(
        id="create_and_verify_product",
        prompt=(
            "Create a product called 'Mechanical Keyboard' with SKU 'KB-TEST-001', "
            "price $89.99, 200 units in stock. "
            "Then verify the product was created correctly by retrieving it."
        ),
        expected_tools=["create_product", "get_product"],
        max_steps=5,
        outcome_checks=[
            {"type": "product_exists", "sku": "KB-TEST-001"},
            {"type": "product_field", "sku": "KB-TEST-001", "field": "name", "value": "Mechanical Keyboard"},
            {"type": "product_field", "sku": "KB-TEST-001", "field": "price", "value": 89.99},
            {"type": "product_field", "sku": "KB-TEST-001", "field": "stock_quantity", "value": 200},
        ],
    ),

    # ── Complex: multi-step workflow ──
    Scenario(
        id="product_and_order",
        prompt=(
            "Create a product called 'USB Hub' with SKU 'UH-TEST-001', "
            "price $19.99, 100 units in stock. "
            "Then create an order for customer 'Jane Smith' (jane@test.com) "
            "buying 3 units of that product."
        ),
        expected_tools=["create_product", "create_order"],
        max_steps=6,
        outcome_checks=[
            {"type": "product_exists", "sku": "UH-TEST-001"},
            {"type": "product_field", "sku": "UH-TEST-001", "field": "price", "value": 19.99},
            {"type": "order_exists", "customer_email": "jane@test.com"},
        ],
    ),
]
