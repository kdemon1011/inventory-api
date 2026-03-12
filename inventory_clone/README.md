# Inventory Clone Environment

A simplified clone of the Inventory gym, demonstrating the MCP-tool pattern.

Created via `openenv init inventory_clone` and customized for tool-based interactions.

## Quick Start

### Run Locally

```bash
cd inventory_clone
uv sync                    # Install dependencies
uv run server              # Start on port 9001
```

### Run with Docker

```bash
cd inventory_clone
docker build -t openenv-inventory-clone -f server/Dockerfile .
docker run -p 9001:9001 openenv-inventory-clone
```

### Connect with Client

```python
from inventory_clone.client import InventoryCloneEnv

with InventoryCloneEnv(base_url="http://localhost:9001") as env:
    env.reset()
    tools = env.list_tools()
    print(f"Available tools: {[t['name'] for t in tools]}")

    result = env.call_tool("create_product", name="Mouse", sku="M1", price=29.99, stock_quantity=100)
    print(f"Created: {result}")

    products = env.call_tool("list_products")
    print(f"Products: {products}")
```

## Architecture

This clone uses **single-process, in-memory storage** (no separate API needed):

```
┌─────────────┐  WebSocket   ┌──────────────────────────┐
│  LLM Agent  │ ──────────►  │  InventoryClone Env      │
│  (client)   │ ◄──────────  │  (OpenEnv, port 9001)    │
└─────────────┘               │  In-memory data store    │
                              └──────────────────────────┘
```

Compare with the full **Inventory gym** (two-process architecture):

```
┌─────────────┐  WebSocket   ┌──────────────────────┐  HTTP    ┌──────────────┐
│  LLM Agent  │ ──────────►  │  Inventory Env       │ ───────► │ Inventory API│
│  (client)   │ ◄──────────  │  (OpenEnv, port 9000)│ ◄─────── │ (port 8000)  │
└─────────────┘               └──────────────────────┘          └──────────────┘
```

## Available Tools

| Tool | Description |
|------|-------------|
| `create_product` | Create a new product (name, sku, price, stock) |
| `list_products` | List all products (optionally active only) |
| `get_product` | Get a product by ID |
| `update_product` | Update product details |
| `create_order` | Create an order with line items |
| `list_orders` | List orders (optionally filter by status) |
| `get_order` | Get order details by ID |

## How This Was Created

1. **Scaffold**: `openenv init inventory_clone`
2. **Customize**: Converted from Gymnasium-style (typed Action/Observation) to MCP-tool pattern
3. **Validate**: `openenv validate inventory_clone/`
4. **Test**: Start server and connect with MCPToolClient
