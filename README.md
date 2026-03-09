# Inventory API — OpenEnv Environment

An inventory management API wrapped as an [OpenEnv](https://github.com/meta-pytorch/OpenEnv) environment, allowing AI agents to interact with products and orders through the standard `reset → step → observe` protocol.

## Architecture

```
AI Agent (MCPToolClient) --WebSocket--> OpenEnv Server (port 9000) --HTTP--> Inventory API (port 8000)
```

The Inventory API (FastAPI + SQLite) runs as a standalone service. The OpenEnv environment wraps it by exposing 10 MCP tools — one for each API operation — so an agent can discover and invoke them through OpenEnv's standard interface.

## Why MCP?

OpenEnv supports MCP (Model Context Protocol) environments where each action the agent can take is defined as a **tool** using `@mcp.tool` decorators. This means:

- The agent doesn't need to know the API routes upfront — it calls `list_tools()` to discover them
- Each tool has a typed schema (name, description, parameters) that an LLM can reason about
- OpenEnv handles all the WebSocket/HTTP plumbing, serialisation, and session management automatically

## How It Connects

| File | Role | OpenEnv Class Used |
|---|---|---|
| `server/inventory_environment.py` | Defines 10 tools (CRUD products + orders) | `MCPEnvironment` |
| `server/app.py` | Auto-generates the server with all routes | `create_app()` |
| `client.py` | WebSocket client for agents/scripts | `MCPToolClient` |
| `models.py` | Re-exports OpenEnv MCP types | — |
| `openenv.yaml` | Environment manifest | — |

## Setup

```bash
# Activate Python environment
source /home/kdemon/Clients/personal_python_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running

You need **two terminals**:

```bash
# Terminal 1 — Start the Inventory API
python main.py
```

```bash
# Terminal 2 — Start the OpenEnv server
python server/app.py
```

## Usage

```python
from client import InventoryEnv
from openenv.core.env_server.mcp_types import CallToolAction

with InventoryEnv(base_url="http://localhost:9000") as env:
    # Start a new episode
    env.reset()

    # Discover available tools
    tools = env.list_tools()
    for t in tools:
        print(f"{t.name}: {t.description}")

    # Call a tool
    result = env.call_tool("list_products", active_only=True)
    print(result)

    # For tools with a 'name' parameter, use step() directly
    env.step(CallToolAction(
        tool_name="create_product",
        arguments={"name": "Mouse", "sku": "M-001", "price": 9.99},
    ))
```

## Testing

```bash
# Both servers must be running first
python test_openenv.py
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
