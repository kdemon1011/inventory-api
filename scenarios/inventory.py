"""
Scenario definitions for the Inventory gym.

Each scenario describes a task that an LLM agent must complete via OpenEnv.
The reward calculator (rewards/base.py) uses these to evaluate agent performance.
Ground truth checks (rewards/inventory_checks.py) verify the DB state after each scenario.

Scenarios use unique SKUs (prefixed with scenario ID, e.g. SC1-, SC2-) to avoid
conflicts when run sequentially in the same database session.

Currently: 10 scenarios ranging from single-tool to complex multi-step workflows.

To add a new scenario: append a Scenario to INVENTORY_SCENARIOS.
To add scenarios for a new gym: create scenarios/<gym>.py and register in run_eval.py.
"""

from rewards.base import Scenario


INVENTORY_SCENARIOS = [
    # ──────────────────────────────────────
    # 1. Simple — single tool
    # ──────────────────────────────────────
    Scenario(
        id="create_product",
        prompt=(
            "Create a product called 'Wireless Mouse' with SKU 'SC1-WM-001', "
            "price $29.99, description 'Ergonomic wireless mouse', "
            "and 50 units in stock."
        ),
        expected_tools=["create_product"],
        max_steps=3,
        outcome_checks=[
            {"type": "product_exists", "sku": "SC1-WM-001"},
            {"type": "product_field", "sku": "SC1-WM-001", "field": "name", "value": "Wireless Mouse"},
            {"type": "product_field", "sku": "SC1-WM-001", "field": "price", "value": 29.99},
            {"type": "product_field", "sku": "SC1-WM-001", "field": "stock_quantity", "value": 50},
        ],
    ),

    # ──────────────────────────────────────
    # 2. Simple — create + read back
    # ──────────────────────────────────────
    Scenario(
        id="create_and_verify_product",
        prompt=(
            "Create a product called 'Mechanical Keyboard' with SKU 'SC2-KB-001', "
            "price $89.99, 200 units in stock. "
            "Then retrieve the product to verify it was created correctly."
        ),
        expected_tools=["create_product", "get_product"],
        max_steps=5,
        outcome_checks=[
            {"type": "product_exists", "sku": "SC2-KB-001"},
            {"type": "product_field", "sku": "SC2-KB-001", "field": "name", "value": "Mechanical Keyboard"},
            {"type": "product_field", "sku": "SC2-KB-001", "field": "price", "value": 89.99},
            {"type": "product_field", "sku": "SC2-KB-001", "field": "stock_quantity", "value": 200},
        ],
    ),

    # ──────────────────────────────────────
    # 3. Medium — create product + create order
    # ──────────────────────────────────────
    Scenario(
        id="product_and_order",
        prompt=(
            "Create a product called 'USB Hub' with SKU 'SC3-UH-001', "
            "price $19.99, 100 units in stock. "
            "Then create an order for customer 'Jane Smith' (jane.sc3@test.com) "
            "buying 3 units of that product."
        ),
        expected_tools=["create_product", "create_order"],
        max_steps=6,
        outcome_checks=[
            {"type": "product_exists", "sku": "SC3-UH-001"},
            {"type": "product_field", "sku": "SC3-UH-001", "field": "price", "value": 19.99},
            {"type": "order_exists", "customer_email": "jane.sc3@test.com"},
        ],
    ),

    # ──────────────────────────────────────
    # 4. Medium — create then update price
    # ──────────────────────────────────────
    Scenario(
        id="update_product_price",
        prompt=(
            "Create a product called 'Bluetooth Speaker' with SKU 'SC4-BS-001', "
            "price $49.99, and 30 units in stock. "
            "Then update the product's price to $39.99."
        ),
        expected_tools=["create_product", "update_product"],
        max_steps=5,
        outcome_checks=[
            {"type": "product_exists", "sku": "SC4-BS-001"},
            {"type": "product_field", "sku": "SC4-BS-001", "field": "name", "value": "Bluetooth Speaker"},
            {"type": "product_field", "sku": "SC4-BS-001", "field": "price", "value": 39.99},
            {"type": "product_field", "sku": "SC4-BS-001", "field": "stock_quantity", "value": 30},
        ],
    ),

    # ──────────────────────────────────────
    # 5. Medium — create then search
    # ──────────────────────────────────────
    Scenario(
        id="search_product",
        prompt=(
            "Create a product called 'Gaming Headset Pro' with SKU 'SC5-GH-001', "
            "price $79.99, description 'Surround sound gaming headset', "
            "and 60 units in stock. "
            "Then search for products matching 'Gaming Headset' and confirm "
            "the product appears in the results."
        ),
        expected_tools=["create_product", "search_products"],
        max_steps=5,
        outcome_checks=[
            {"type": "product_exists", "sku": "SC5-GH-001"},
            {"type": "product_field", "sku": "SC5-GH-001", "field": "name", "value": "Gaming Headset Pro"},
            {"type": "product_field", "sku": "SC5-GH-001", "field": "price", "value": 79.99},
        ],
    ),

    # ──────────────────────────────────────
    # 6. Medium — create then deactivate
    # ──────────────────────────────────────
    Scenario(
        id="deactivate_product",
        prompt=(
            "Create a product called 'Old Webcam' with SKU 'SC6-OW-001', "
            "price $15.00, and 5 units in stock. "
            "Then deactivate the product (set is_active to false) because "
            "it is discontinued."
        ),
        expected_tools=["create_product", "update_product"],
        max_steps=5,
        outcome_checks=[
            {"type": "product_exists", "sku": "SC6-OW-001"},
            {"type": "product_field", "sku": "SC6-OW-001", "field": "is_active", "value": False},
        ],
    ),

    # ──────────────────────────────────────
    # 7. Medium — create two products, list them
    # ──────────────────────────────────────
    Scenario(
        id="bulk_product_creation",
        prompt=(
            "Create two products:\n"
            "  1. 'Monitor Stand' with SKU 'SC7-MS-001', price $34.99, 40 units in stock.\n"
            "  2. 'Desk Lamp' with SKU 'SC7-DL-001', price $24.99, 75 units in stock.\n"
            "Then list all products to confirm both were added."
        ),
        expected_tools=["create_product", "list_products"],
        max_steps=6,
        outcome_checks=[
            {"type": "product_exists", "sku": "SC7-MS-001"},
            {"type": "product_field", "sku": "SC7-MS-001", "field": "price", "value": 34.99},
            {"type": "product_exists", "sku": "SC7-DL-001"},
            {"type": "product_field", "sku": "SC7-DL-001", "field": "price", "value": 24.99},
        ],
    ),

    # ──────────────────────────────────────
    # 8. Complex — full order with verification
    # ──────────────────────────────────────
    Scenario(
        id="full_order_workflow",
        prompt=(
            "Create a product called 'Ergonomic Chair' with SKU 'SC8-EC-001', "
            "price $299.99, and 20 units in stock. "
            "Then create an order for customer 'Bob Wilson' (bob.sc8@test.com) "
            "buying 2 units of the chair. "
            "Finally, retrieve the order details to verify it was created correctly."
        ),
        expected_tools=["create_product", "create_order", "get_order_detail"],
        max_steps=8,
        outcome_checks=[
            {"type": "product_exists", "sku": "SC8-EC-001"},
            {"type": "product_field", "sku": "SC8-EC-001", "field": "price", "value": 299.99},
            {"type": "order_exists", "customer_email": "bob.sc8@test.com"},
            {"type": "order_has_items", "customer_email": "bob.sc8@test.com", "expected_count": 1},
        ],
    ),

    # ──────────────────────────────────────
    # 9. Complex — multi-item order
    # ──────────────────────────────────────
    Scenario(
        id="multi_item_order",
        prompt=(
            "Create two products:\n"
            "  1. 'Notebook' with SKU 'SC9-NB-001', price $12.99, 500 units in stock.\n"
            "  2. 'Pen Set' with SKU 'SC9-PS-001', price $8.49, 300 units in stock.\n"
            "Then create a single order for customer 'Alice Brown' (alice.sc9@test.com) "
            "that contains both products: 10 notebooks and 5 pen sets."
        ),
        expected_tools=["create_product", "create_order"],
        max_steps=8,
        outcome_checks=[
            {"type": "product_exists", "sku": "SC9-NB-001"},
            {"type": "product_exists", "sku": "SC9-PS-001"},
            {"type": "order_exists", "customer_email": "alice.sc9@test.com"},
            {"type": "order_has_items", "customer_email": "alice.sc9@test.com", "expected_count": 2},
        ],
    ),

    # ──────────────────────────────────────
    # 10. Complex — create, update, order, verify
    # ──────────────────────────────────────
    Scenario(
        id="price_change_then_order",
        prompt=(
            "Create a product called 'Wireless Charger' with SKU 'SC10-WC-001', "
            "price $45.00, and 150 units in stock. "
            "The price is wrong — update it to $35.00. "
            "Then create an order for customer 'Charlie Davis' (charlie.sc10@test.com) "
            "buying 5 units of the charger at the corrected price. "
            "Finally, retrieve the order summary to confirm the order."
        ),
        expected_tools=["create_product", "update_product", "create_order", "get_order_summary"],
        max_steps=10,
        outcome_checks=[
            {"type": "product_exists", "sku": "SC10-WC-001"},
            {"type": "product_field", "sku": "SC10-WC-001", "field": "price", "value": 35.00},
            {"type": "order_exists", "customer_email": "charlie.sc10@test.com"},
        ],
    ),
]
