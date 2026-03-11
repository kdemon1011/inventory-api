# Inventory Gym

Inventory management API wrapped as an [OpenEnv](https://github.com/meta-pytorch/OpenEnv) MCP environment. Exposes 10 tools (product + order CRUD) that an AI agent can discover and call through OpenEnv's standard protocol.

## Architecture

```
LLM Agent ──► AgentRunner ──► OpenEnv Server (port 9000) ──HTTP──► Inventory API (port 8000) ──► SQLite DB
```

The LLM never calls the Inventory API directly. All interactions go through OpenEnv via `env.step()`.

## Files

| File | Role | OpenEnv Class |
|---|---|---|
| `server/inventory_environment.py` | 10 MCP tools (CRUD products + orders) | `MCPEnvironment` |
| `server/app.py` | Auto-generated server (HTTP + WebSocket) | `create_app()` |
| `client.py` | WebSocket client for manual tests | `MCPToolClient` |
| `openenv.yaml` | Environment manifest | — |
| `config.py` | Centralized config (ports, DB path) | — |
| `main.py` | FastAPI app (products + orders API) | — |
| `tests_archived/` | Pre-OpenEnv API unit tests (archived) | — |

## Running

```bash
# From this directory (inventory/)

# Terminal 1 — Inventory API on port 8000
python main.py

# Terminal 2 — OpenEnv server on port 9000
python -m uvicorn server.app:app --host 0.0.0.0 --port 9000
```

## Running LLM Evaluation

```bash
# From the repo root (one level up)

# Reset DB for a clean run
rm -f inventory/data/app.db

# Restart servers, then:
python run_eval.py --gym inventory --model gpt-4o --save --trajectory
```

See the [main README](../README.md) for full CLI options and available models.

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
- Simple single-tool tasks (create a product)
- Multi-step workflows (create product + verify + update price)
- Complex workflows (bulk creation, full order lifecycle with stock tracking)

## Configuration

Ports and DB path are configured in `config.py`, which reads from `.env` (inside this folder):

```env
API_PORT=8000
OPENENV_PORT=9000
INVENTORY_API_URL=http://localhost:8000
```
