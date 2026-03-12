# Inventory Gym

Inventory management API wrapped as an [OpenEnv](https://github.com/meta-pytorch/OpenEnv) MCP environment. Exposes 10 tools (product + order CRUD) that an AI agent can discover and call through OpenEnv's standard protocol.

## Architecture

```
┌─────────────────┐         ┌──────────────────────┐         ┌──────────────────┐         ┌──────────┐
│  LLM Agent      │         │  OpenEnv Server      │         │  Inventory API   │         │  SQLite  │
│  (run_eval.py)  │ ──WS──► │  (port 9000)         │ ──HTTP─► │  (port 8000)     │ ──────► │  DB      │
│                 │ ◄────── │  MCPEnvironment      │ ◄────── │  FastAPI         │ ◄────── │          │
└─────────────────┘         └──────────────────────┘         └──────────────────┘         └──────────┘
   Decides WHAT to do          Wraps API as MCP tools           CRUD endpoints              Persistent
   (reasoning via LLM)         Handles reset/step/state         Products + Orders           storage
```

### Flow

1. **LLM Agent** connects to the OpenEnv server via WebSocket (`ws://localhost:9000/ws`)
2. Agent calls `list_tools()` → OpenEnv returns 10 available tools (product + order CRUD)
3. Agent reasons about the task and decides which tool to call
4. Agent sends `env.step(CallToolAction(...))` → OpenEnv executes the tool
5. The tool (inside `inventory_environment.py`) makes HTTP calls to the Inventory API
6. Result flows back: API → Environment → Agent
7. After all steps, the reward system queries the API directly to verify ground truth

The LLM **never calls the Inventory API directly**. All interactions go through OpenEnv via `env.step()`.

## Files

| File | Role | OpenEnv Class |
|---|---|---|
| `server/inventory_environment.py` | 10 MCP tools (CRUD products + orders) | `MCPEnvironment` |
| `server/app.py` | Auto-generated server (HTTP + WebSocket) | `create_app()` |
| `Dockerfile` | Docker image (API + OpenEnv in one container) | — |
| `client.py` | Client + AutoEnv type aliases | `MCPToolClient` |
| `openenv.yaml` | Environment manifest | — |
| `pyproject.toml` | Package config (validate / build / uv run) | — |
| `config.py` | Centralized config (ports, DB path) | — |
| `main.py` | FastAPI app (products + orders API) | — |
| `tests_archived/` | Pre-OpenEnv API unit tests (archived) | — |

## Running the Gym

### Step 0: Install for AutoEnv discovery (one-time)

```bash
# From the repo root
pip install -e inventory/
```

This makes the gym discoverable by AutoEnv. Verify:
```bash
python -c "from openenv import AutoEnv; AutoEnv.list_environments()"
```

### Start the Gym (Docker)

Docker packages both the Inventory API and OpenEnv server into a single container:

```bash
# 1. Build the image (one-time, from this directory)
docker build -t openenv-inventory .

# 2. Run the container
#    Port 9000 = OpenEnv server (AutoEnv connects here automatically)
#    Port 8000 = Inventory API (ground truth checker connects here)
docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory

# 3. Verify both servers are ready
curl http://localhost:9000/health    # → {"status": "healthy"}
curl http://localhost:8000/products  # → [...]

# 4. Run an evaluation (AutoEnv discovers and connects automatically)
cd ..  # repo root
python run_eval.py --gym inventory --model gpt-4o --save --trajectory

# 5. Stop and remove when done
docker stop inventory && docker rm inventory
```

> **No manual servers required.** Docker runs both the Inventory API (port 8000) and the OpenEnv server (port 9000) inside a single container. `run_eval.py` uses AutoEnv to auto-discover the gym and auto-derive the port from `openenv.yaml`.

### Validate

Verify the gym is properly configured for deployment:

```bash
# From the repo root
openenv validate inventory/
```

Expected output:

```
[OK] inventory: Ready for multi-mode deployment
  [YES] docker
  [YES] openenv_serve
  [YES] uv_run
  [YES] python_module
```

## Resetting Between Runs

Each model evaluation should start with a clean database. With Docker, simply stop and restart the container:

```bash
# Stop and remove the current container
docker stop inventory && docker rm inventory

# Start a fresh container (clean database)
docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory
```

## Available Tools

| Tool | Description |
|---|---|
| `create_product` | Create a new product |
| `list_products` | List all products |
| `get_product` | Get product by ID |
| `search_products` | Search products by name/description |
| `update_product` | Update product details |
| `create_order` | Create a new order |
| `list_orders` | List orders (optionally filtered) |
| `get_order` | Get order by ID |
| `get_order_detail` | Get order with item breakdown |
| `get_order_summary` | Get order summary |

## Reward Modes

Two reward modes can be used when evaluating this gym. Both share the same ground truth checker (`rewards/inventory_checks.py`) — the difference is how per-step performance is scored.

```bash
# Default: episode-level reward (rewards/base.py)
python run_eval.py --gym inventory --model gpt-4o --reward-mode custom

# OpenEnv per-step reward (rewards/transforms/inventory.py + ground truth)
python run_eval.py --gym inventory --model gpt-4o --reward-mode openenv
```

### Custom Rewards (`--reward-mode custom`)

Calculated **after the episode ends** by `rewards/base.py → RewardCalculator`:

| Component | Weight | Calculation |
|---|---|---|
| **Structural** | 0.25 | `0.6 × F1(expected_tools, used_tools) + 0.4 × success_rate` |
| **Ground Truth** | 0.60 | `passed_checks / total_checks` (queries SQLite DB) |
| **Efficiency** | 0.15 | `min(expected_steps / actual_steps, 1.0)` |
| **Penalty** | -1.0 | If all steps succeed but 0 ground truth checks pass |

**Total** = `0.25 × structural + 0.60 × ground_truth + 0.15 × efficiency + penalty`

Example — `create_and_verify_product` (expected tools: `create_product`, `get_product`):

| Step | Tool | Success | F1 Match |
|---|---|---|---|
| 1 | `create_product` | ✅ | ✅ expected |
| 2 | `get_product` | ✅ | ✅ expected |

- Structural: 0.6 × 1.0 (F1) + 0.4 × 1.0 (success) = **1.00**
- Ground Truth: 2/2 checks pass = **1.00**
- Efficiency: min(2/2, 1.0) = **1.00**
- Total: 0.25 × 1.00 + 0.60 × 1.00 + 0.15 × 1.00 = **1.00**

### OpenEnv Transform Rewards (`--reward-mode openenv`)

Calculated **per-step as each tool call returns** by `rewards/transforms/inventory.py → InventoryStepTransform`, then combined with ground truth by `OpenEnvRewardCalculator`:

| Component | Weight | Calculation |
|---|---|---|
| **Step Rewards** | 0.40 | Avg per-step reward, normalized [-0.5, 1.0] → [0, 1] |
| **Ground Truth** | 0.60 | `passed_checks / total_checks` (same DB verification) |
| **Efficiency** | — | Always 0.0 (transform can't see expected step count) |
| **Penalty** | -1.0 | If all step rewards > 0 but 0 ground truth checks pass |

**Total** = `0.40 × step_score + 0.60 × ground_truth + penalty`

The `InventoryStepTransform` scores each tool call by inspecting the API response structure:

| Result type | Reward | Example tool call |
|---|---|---|
| Entity with `id` (dict) | **1.0** | `create_product` → `{"id": 1, "name": "Widget"}` |
| Non-empty list | **0.8** | `list_products` → `[{"id": 1, ...}, {"id": 2, ...}]` |
| Empty list / minimal | **0.5** | `search_products(name="xyz")` → `[]` |
| Error | **-0.5** | Invalid SKU → `{"error": "..."}` |

Example — `price_change_then_order` (4 steps):

| Step | Tool | Result | Per-step reward |
|---|---|---|---|
| 1 | `create_product` | `{"id": 1, "price": 29.99}` | 1.0 |
| 2 | `update_product` | `{"id": 1, "price": 24.99}` | 1.0 |
| 3 | `create_order` | `{"id": 1, "items": [...]}` | 1.0 |
| 4 | `get_order_summary` | `{"id": 1, "total": 49.98}` | 0.5 |

- Step score: avg = 0.875, normalized = (0.875 + 0.5) / 1.5 = **0.92**
- Ground Truth: 2 of 3 checks pass = **0.67**
- Total: 0.40 × 0.92 + 0.60 × 0.67 = **0.77**

### Side-by-side comparison

| Aspect | Custom | OpenEnv Transform |
|---|---|---|
| **When** evaluated | After episode ends | Per-step as it happens |
| **Tool selection** | ✅ F1 score against expected tools | ❌ Can't see scenario context |
| **Success quality** | Boolean (pass/fail) | Graded (1.0 / 0.8 / 0.5 / -0.5) |
| **Result inspection** | ❌ Doesn't look at response content | ✅ Validates response structure |
| **Efficiency** | ✅ Penalizes extra steps | ❌ Not applicable |
| **Ground truth** | ✅ Same DB checks (0.60 weight) | ✅ Same DB checks (0.60 weight) |
| **Hallucination** | ✅ -1.0 penalty | ✅ -1.0 penalty |
| **Best for** | "Did the agent follow the plan?" | "Did each step produce quality output?" |

## Scenarios

10 scenarios are defined in `scenarios/inventory.py`, ranging from:

- **Simple** — Single-tool tasks (create a product, list products)
- **Multi-step** — Create product → verify → update price
- **Complex** — Bulk creation, full order lifecycle with stock tracking, multi-step operations

Each scenario defines:
- A natural language prompt for the LLM
- Expected tools the agent should call
- Max steps allowed
- Outcome checks (ground truth verification against the database)

## Configuration

Ports and DB path are configured in `config.py`, which reads from `.env` (inside this folder):

```env
API_PORT=8000
OPENENV_PORT=9000
INVENTORY_API_URL=http://localhost:8000
```

API keys for LLM providers are in the root `.env` file:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```
