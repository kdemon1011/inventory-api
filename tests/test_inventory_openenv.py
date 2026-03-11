"""
End-to-End Manual Test for the Inventory OpenEnv Environment + Reward System.

Runs 3 hard-coded scenarios against the real OpenEnv server (no LLM),
logs each step, verifies outcomes against the database, and prints
the reward breakdown.

This is for debugging the environment + reward system — not for LLM evaluation.
For LLM evaluation, use run_eval.py instead.

Before running:
  Terminal 1: cd inventory && python main.py
  Terminal 2: cd inventory && python -m uvicorn server.app:app --host 0.0.0.0 --port 9000

Then (from repo root):
  python tests/test_inventory_openenv.py
"""

import os
import sys
import time

# Add repo root to path so we can import rewards/, scenarios/, inventory/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from inventory.client import InventoryEnv
from openenv.core.env_server.mcp_types import CallToolAction

from rewards import RewardCalculator, EpisodeLog
from rewards.inventory_checks import InventoryChecker
from scenarios import INVENTORY_SCENARIOS


def divider(text: str = ""):
    print(f"\n{'='*60}")
    if text:
        print(f"  {text}")
        print(f"{'='*60}")


def run_scenario_create_product(env, episode: EpisodeLog):
    """Simulate an agent completing the 'create_product' scenario."""

    # Agent calls create_product
    result = env.step(CallToolAction(
        tool_name="create_product",
        arguments={
            "name": "Wireless Mouse",
            "sku": "WM-TEST-001",
            "price": 29.99,
            "description": "Ergonomic wireless mouse",
            "stock_quantity": 50,
        },
    ))
    is_error = getattr(result.observation, "is_error", False) if result.observation else True
    episode.add_step(
        tool_name="create_product",
        arguments={"name": "Wireless Mouse", "sku": "WM-TEST-001", "price": 29.99, "stock_quantity": 50},
        success=not is_error,
        result=result.observation,
    )
    print(f"  create_product → success={not is_error}")


def run_scenario_create_and_verify(env, episode: EpisodeLog):
    """Simulate an agent completing the 'create_and_verify_product' scenario."""

    # Step 1: Create the product
    result = env.step(CallToolAction(
        tool_name="create_product",
        arguments={
            "name": "Mechanical Keyboard",
            "sku": "KB-TEST-001",
            "price": 89.99,
            "description": "Cherry MX switches",
            "stock_quantity": 200,
        },
    ))
    is_error = getattr(result.observation, "is_error", False) if result.observation else True
    episode.add_step(
        tool_name="create_product",
        arguments={"name": "Mechanical Keyboard", "sku": "KB-TEST-001", "price": 89.99, "stock_quantity": 200},
        success=not is_error,
        result=result.observation,
    )
    print(f"  create_product → success={not is_error}")

    # Step 2: Verify by listing products
    products = env.call_tool("list_products", active_only=True)
    found = any(
        (p.get("sku") == "KB-TEST-001" if isinstance(p, dict) else False)
        for p in (products if isinstance(products, list) else [])
    )
    episode.add_step(
        tool_name="list_products",
        arguments={"active_only": True},
        success=True,
        result=products,
    )
    print(f"  list_products → found KB-TEST-001: {found}")


def run_scenario_product_and_order(env, episode: EpisodeLog):
    """Simulate an agent completing the 'product_and_order' scenario."""

    # Step 1: Create product
    result = env.step(CallToolAction(
        tool_name="create_product",
        arguments={
            "name": "USB Hub",
            "sku": "UH-TEST-001",
            "price": 19.99,
            "description": "4-port USB 3.0 hub",
            "stock_quantity": 100,
        },
    ))
    is_error = getattr(result.observation, "is_error", False) if result.observation else True

    # Extract product ID from result for the order
    product_id = None
    obs = result.observation
    if hasattr(obs, "data") and isinstance(obs.data, dict):
        product_id = obs.data.get("id")
    elif hasattr(obs, "structured_content") and isinstance(obs.structured_content, dict):
        product_id = obs.structured_content.get("id")

    episode.add_step(
        tool_name="create_product",
        arguments={"name": "USB Hub", "sku": "UH-TEST-001", "price": 19.99, "stock_quantity": 100},
        success=not is_error,
        result=obs,
    )
    print(f"  create_product → success={not is_error}, product_id={product_id}")

    # Step 2: Create order (use product_id=1 as fallback)
    order_product_id = product_id or 1
    result = env.step(CallToolAction(
        tool_name="create_order",
        arguments={
            "customer_name": "Jane Smith",
            "customer_email": "jane@test.com",
            "items": [{"product_id": order_product_id, "quantity": 3}],
        },
    ))
    is_error = getattr(result.observation, "is_error", False) if result.observation else True
    episode.add_step(
        tool_name="create_order",
        arguments={"customer_name": "Jane Smith", "customer_email": "jane@test.com", "items": [{"product_id": order_product_id, "quantity": 3}]},
        success=not is_error,
        result=result.observation,
    )
    print(f"  create_order → success={not is_error}")


# Map scenario IDs to their runner functions
SCENARIO_RUNNERS = {
    "create_product": run_scenario_create_product,
    "create_and_verify_product": run_scenario_create_and_verify,
    "product_and_order": run_scenario_product_and_order,
}


def main():
    divider("Inventory OpenEnv — Reward System Test")
    print()

    calculator = RewardCalculator()

    with InventoryEnv(base_url="http://localhost:9000") as env:
        with InventoryChecker(api_url="http://localhost:8000") as checker:

            for scenario in INVENTORY_SCENARIOS:
                runner = SCENARIO_RUNNERS.get(scenario.id)
                if not runner:
                    print(f"  ⚠ No runner for scenario '{scenario.id}', skipping")
                    continue

                divider(f"Scenario: {scenario.id}")
                print(f"  Prompt: {scenario.prompt[:80]}...")
                print(f"  Expected tools: {scenario.expected_tools}")
                print()

                # Reset environment for each scenario
                env.reset()
                episode = EpisodeLog()

                # Run the scenario (simulate agent actions)
                print("  — Agent Actions —")
                runner(env, episode)

                # Verify outcomes against the real database
                print()
                print("  — Ground Truth Verification —")
                outcome_results = checker.check_all(scenario.outcome_checks)
                for check, passed in zip(scenario.outcome_checks, outcome_results):
                    status = "✅" if passed else "❌"
                    print(f"  {status} {check['type']}: {check.get('field', check.get('sku', check.get('customer_email', '')))}")

                # Calculate reward
                breakdown = calculator.calculate(
                    episode=episode,
                    scenario=scenario,
                    outcome_results=outcome_results,
                )

                print()
                print("  — Reward Breakdown —")
                print(breakdown.summary())
                print()
                print(f"  Details: {breakdown.details}")

    divider("All Scenarios Complete")


if __name__ == "__main__":
    main()
