"""
OpenEnv End-to-End Test Script.

This script simulates an AI agent interacting with your Inventory environment.
It tests the complete flow: reset → step → step → step → state.

Before running this, make sure BOTH servers are running:
  Terminal 1: cd /home/kdemon/Clients/huzzle/inventory-api && python main.py
  Terminal 2: cd /home/kdemon/Clients/huzzle/inventory-api/server && python app.py

Then run:
  python test_openenv.py
"""

from client import InventoryEnvClient


def print_divider(text: str = ""):
    """Print a nice divider for readability."""
    print(f"\n{'='*60}")
    if text:
        print(f"  {text}")
        print(f"{'='*60}")


def main():
    print_divider("🚀 OpenEnv Inventory Environment — End-to-End Test")
    print()

    # Connect to the OpenEnv server (port 9000, NOT the inventory API directly)
    with InventoryEnvClient("http://localhost:9000") as client:

        # ── Health Check ──
        print("1️⃣  Checking health...")
        health = client.health()
        print(f"   Status: {health['status']}")
        print(f"   Connected to: {health['inventory_api_url']}")

        # ── Reset (Start Episode) ──
        print_divider("2️⃣  RESET — Starting a new episode")
        result = client.reset(task_index=0)

        obs = result["observation"]
        state = result["state"]
        print(f"   Episode ID: {state['episode_id']}")
        print(f"   📋 Task: {obs['data']['task']}")
        print(f"   Available tools: {obs['available_tools']}")
        print(f"   Step: {state['step_count']}, Reward: {state['total_reward']}")

        # ── Step 1: Create a product ──
        print_divider("3️⃣  STEP 1 — Creating a product")
        result = client.step("create_product", {
            "name": "Wireless Mouse",
            "sku": "WM-001",
            "price": 29.99,
            "stock_quantity": 100,
        })
        obs = result["observation"]
        print(f"   Success: {obs['success']}")
        print(f"   Reward: {result['reward']}")
        print(f"   Done: {result['done']}")
        if obs["success"]:
            print(f"   Created product: {obs['data']}")
        else:
            print(f"   Error: {obs.get('error')}")

        # ── Step 2: List all products (verify the product exists) ──
        print_divider("4️⃣  STEP 2 — Listing all products")
        result = client.step("list_products", {})
        obs = result["observation"]
        print(f"   Success: {obs['success']}")
        print(f"   Reward: {result['reward']}")
        if obs["success"]:
            products = obs["data"]
            print(f"   Found {len(products)} product(s):")
            for p in products:
                print(f"     - {p['name']} (SKU: {p['sku']}, Price: ${p['price']})")

        # ── Step 3: Create an order ──
        print_divider("5️⃣  STEP 3 — Creating an order")
        result = client.step("create_order", {
            "customer_name": "Alice Johnson",
            "customer_email": "alice@example.com",
            "items": [{"product_id": 1, "quantity": 2}],
        })
        obs = result["observation"]
        print(f"   Success: {obs['success']}")
        print(f"   Reward: {result['reward']}")
        if obs["success"]:
            print(f"   Order: {obs['data']}")
        else:
            print(f"   Error: {obs.get('error')}")

        # ── Step 4: Try an INVALID tool (to see penalty) ──
        print_divider("6️⃣  STEP 4 — Testing invalid tool (should get penalty)")
        result = client.step("delete_everything", {})
        obs = result["observation"]
        print(f"   Success: {obs['success']}")
        print(f"   Reward: {result['reward']}  ← NEGATIVE (penalty!)")
        print(f"   Error: {obs.get('error')}")

        # ── Check Final State ──
        print_divider("7️⃣  FINAL STATE")
        state_result = client.state()
        state = state_result["state"]
        history = state_result["action_history"]
        print(f"   Episode ID: {state['episode_id']}")
        print(f"   Steps taken: {state['step_count']}")
        print(f"   Total reward: {state['total_reward']}")
        print(f"   Task completed: {state['task_completed']}")
        print()
        print("   📜 Action History:")
        for h in history:
            print(f"     Step {h['step']}: {h['tool']}({h['parameters']})")

    print_divider("✅ TEST COMPLETE!")
    print()
    print("What you just saw is EXACTLY what an AI agent would experience.")
    print("In Part 2, an LLM will make these same calls automatically,")
    print("and learn from the rewards to get better at the tasks!")
    print()


if __name__ == "__main__":
    main()
