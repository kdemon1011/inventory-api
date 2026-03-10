# Inventory Gym

Inventory management API wrapped as an [OpenEnv](https://github.com/meta-pytorch/OpenEnv) MCP environment. Exposes 10 tools (product + order CRUD) that an AI agent can discover and call.

## Architecture

```
AI Agent (MCPToolClient) --WebSocket--> OpenEnv Server (port 9000) --HTTP--> Inventory API (port 8000)
```

## Files

| File | Role | OpenEnv Class |
|---|---|---|
| `server/inventory_environment.py` | 10 MCP tools (CRUD products + orders) | `MCPEnvironment` |
| `server/app.py` | Auto-generated server (HTTP + WebSocket) | `create_app()` |
| `client.py` | WebSocket client for agents | `MCPToolClient` |
| `openenv.yaml` | Environment manifest | — |

## Running

```bash
# From this directory (inventory/)
python main.py            # Terminal 1 — Inventory API on port 8000
python server/app.py      # Terminal 2 — OpenEnv server on port 9000
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
