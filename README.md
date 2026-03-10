# RL Gyms — OpenEnv Environments

A collection of reinforcement learning environments built on Meta's [OpenEnv](https://github.com/meta-pytorch/OpenEnv) framework. Each gym wraps a real API as an MCP-based environment that AI agents can interact with through the standard `reset → step → observe` protocol.

## How It Works

Each gym has three components:

1. **The API** — a real FastAPI service (e.g., inventory management with products and orders)
2. **The OpenEnv Server** — wraps the API as an MCP environment, exposing tools via WebSocket
3. **The Client** — connects to the OpenEnv server to discover and call tools

```
AI Agent / RL Trainer
        │
        │  WebSocket (port 9000)
        ▼
OpenEnv Server (MCPEnvironment + create_app)
        │
        │  HTTP (port 8000)
        ▼
Real API (FastAPI + Database)
```

The agent doesn't call the API directly. Instead, it uses OpenEnv's `list_tools()` to discover available actions and `call_tool()` to execute them. This gives the agent a consistent interface across any gym.

## Repository Structure

```
├── inventory/                  ← Inventory Management gym
│   ├── main.py                 ← FastAPI app (products + orders)
│   ├── server/                 ← OpenEnv environment + server
│   ├── client.py               ← MCPToolClient wrapper
│   ├── models/                 ← SQLAlchemy models
│   ├── routers/                ← API route handlers
│   ├── schemas/                ← Pydantic schemas
│   ├── services/               ← Business logic
│   ├── tests/                  ← API unit tests
│   └── README.md               ← Gym-specific docs
│
├── rewards/                    ← Shared reward system
│   ├── base.py                 ← RewardCalculator (gym-agnostic)
│   └── inventory_checks.py     ← Inventory ground truth verification
│
├── scenarios/                  ← Scenario definitions per gym
│   └── inventory.py            ← Inventory scenarios (3 scenarios)
│
├── tests/                      ← OpenEnv integration tests
│   └── test_inventory_openenv.py
│
├── requirements.txt            ← Shared dependencies
└── pytest.ini                  ← Pytest configuration
```

## Setup

```bash
# Activate Python environment
source /home/kdemon/Clients/personal_python_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Dependencies

- `openenv-core>=0.2.1` — Meta's OpenEnv framework
- `fastmcp>=0.2.0` — MCP tool definitions
- `fastapi`, `uvicorn` — API server
- `httpx` — HTTP client for tool→API calls
- `sqlalchemy`, `aiosqlite` — Database

## Running a Gym

Each gym needs **two processes**: the API and the OpenEnv server.

### Inventory Gym

```bash
# Terminal 1 — Start the Inventory API (port 8000)
cd inventory && python main.py

# Terminal 2 — Start the OpenEnv server (port 9000)
cd inventory && python server/app.py
```

### Run the Integration Test (from repo root)

```bash
python tests/test_inventory_openenv.py
```

This runs all scenarios, verifies outcomes against the real database, and prints a reward breakdown for each.

### Quick Usage Example

```python
from inventory.client import InventoryEnv
from openenv.core.env_server.mcp_types import CallToolAction

with InventoryEnv(base_url="http://localhost:9000") as env:
    env.reset()

    # Discover tools
    tools = env.list_tools()

    # Call a tool
    result = env.call_tool("list_products", active_only=True)

    # For tools with a 'name' parameter, use step() directly
    env.step(CallToolAction(
        tool_name="create_product",
        arguments={"name": "Mouse", "sku": "M-001", "price": 9.99},
    ))
```

## Reward System

The reward calculator (`rewards/base.py`) is **gym-agnostic** — it works with any gym. It computes an episode-level reward from 4 components:

| Component | Weight | What it checks |
|---|---|---|
| **Structural** | 0.20 | Did the agent call the right tools? (F1 score + execution success) |
| **Ground Truth** | 0.45 | Does the database state match the expected outcome? |
| **Consistency** | 0.25 | Does the agent's claim match reality? (anti-hallucination) |
| **Efficiency** | 0.10 | Did the agent solve it in a reasonable number of steps? |

A **hallucination penalty** (-1.0) is applied if all tool calls "succeeded" but the database shows nothing actually happened.

Each gym provides its own:
- **Checker** (`rewards/<gym>_checks.py`) — verifies ground truth against the API/DB
- **Scenarios** (`scenarios/<gym>.py`) — defines tasks with expected tools and outcome checks

## Adding a New Gym

1. Create a folder: `my_gym/` with your API, OpenEnv environment, and client
2. Add `rewards/my_gym_checks.py` — ground truth verification (DB/API queries)
3. Add `scenarios/my_gym.py` — scenario definitions with expected outcomes
4. Add `tests/test_my_gym_openenv.py` — integration test
5. Add `my_gym/README.md` — gym-specific documentation

The `RewardCalculator`, `EpisodeLog`, `Scenario`, and `RewardBreakdown` classes from `rewards/base.py` work with any gym — no modifications needed.

## Available Gyms

| Gym | Description | Tools | Status |
|---|---|---|---|
| `inventory/` | Inventory management (products + orders) | 10 | ✅ Active |
