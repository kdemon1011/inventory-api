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
| `client.py` | WebSocket client for manual tests | `MCPToolClient` |
| `openenv.yaml` | Environment manifest | — |
| `pyproject.toml` | Package config (validate / build / uv run) | — |
| `config.py` | Centralized config (ports, DB path) | — |
| `main.py` | FastAPI app (products + orders API) | — |
| `tests_archived/` | Pre-OpenEnv API unit tests (archived) | — |

## Running the Gym

### Option A: Docker (preferred)

Docker packages both the Inventory API and OpenEnv server into a single container. No local setup required — just build and run.

```bash
# 1. Build the image (from repo root)
openenv build inventory/
# OR: cd inventory && docker build -t openenv-inventory .

# 2. Run the container
#    Port 9000 = OpenEnv server (agent connects here)
#    Port 8000 = Inventory API (ground truth checker connects here)
docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory

# 3. Verify it's running
curl http://localhost:9000/health
curl http://localhost:8000/health

# 4. Run an evaluation (from repo root)
python run_eval.py --gym inventory --model gpt-4o --save --trajectory

# 5. Stop and remove when done
docker stop inventory && docker rm inventory
```

### Option B: `uv run server` (local development)

For local development and debugging, run the API and OpenEnv server as separate processes.

```bash
# From this directory (inventory/)

# Terminal 1 — Start the Inventory API on port 8000
python main.py

# Terminal 2 — Start the OpenEnv server on port 9000
uv run server
```

> `uv run server` creates an isolated `.venv` inside this folder on first run (may take a minute). Subsequent runs are instant. It reads the entry point from `pyproject.toml`.

Then from the repo root:

```bash
python run_eval.py --gym inventory --model gpt-4o --save --trajectory
```

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

Each model evaluation should start with a clean database:

```bash
# Kill any running servers
lsof -ti :8000 -ti :9000 | xargs kill -9 2>/dev/null

# Delete the database
rm -f inventory/data/app.db

# Restart servers (Option A or B above)
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
