# How OpenEnv Works

[OpenEnv](https://github.com/meta-pytorch/OpenEnv) is Meta's framework for creating isolated, tool-based environments that AI agents can interact with. Think of it as a bridge: one side is an LLM that reasons and decides what to do, the other side is a real system (API, database, browser) that executes actions. OpenEnv handles everything in between.

## The Core Idea

An AI agent should never call tools directly. Instead:

1. The agent connects to an OpenEnv server
2. It discovers what tools are available (`list_tools()`)
3. It decides what to do (reasoning)
4. It sends an action through OpenEnv (`call_tool()`)
5. OpenEnv executes the action and returns the observation
6. The agent observes the result and decides the next action
7. Repeat until done

```
┌─────────────────┐                    ┌──────────────────┐                    ┌──────────────────┐
│                  │   1. list_tools()  │                  │                    │                  │
│   LLM Agent     │ ─────────────────► │   OpenEnv        │                    │   Real System    │
│   (reasoning)   │                    │   Server         │   HTTP / SDK       │   (API, DB,      │
│                  │   2. call_tool()   │   (port 9000)    │ ─────────────────► │    browser)      │
│                  │ ─────────────────► │                  │                    │                  │
│                  │   3. observation   │                  │ ◄───────────────── │                  │
│                  │ ◄───────────────── │                  │                    │                  │
└─────────────────┘                    └──────────────────┘                    └──────────────────┘
```

## OpenEnv Key Components

### MCPEnvironment

The base class for tool-based environments. Instead of defining a fixed action space (like Gymnasium), you define **tools** using FastMCP decorators:

```python
from openenv.core.env_server.mcp_environment import MCPEnvironment
from fastmcp import FastMCP

class MyEnvironment(MCPEnvironment):
    def __init__(self):
        mcp = FastMCP("my_env")

        @mcp.tool()
        def do_something(param: str) -> dict:
            """Tool description — the agent sees this."""
            return {"result": "done"}

        super().__init__(mcp)  # registers all tools
```

When the agent calls `list_tools()`, OpenEnv returns all registered tools with their names, descriptions, and parameter schemas. The agent then calls `call_tool("do_something", param="value")` and OpenEnv routes it to the right function.

### create_app()

Auto-generates a FastAPI server with all the standard endpoints:

```python
from openenv.core.env_server.http_server import create_app

app = create_app(MyEnvironment, MCPAction, CallToolObservation, env_name="my_env")
```

This single line creates:
- `POST /reset` — Reset the environment
- `POST /step` — Execute an action (tool call)
- `GET /state` — Get current environment state
- `GET /metadata` — Environment name, version, description (from `get_metadata()`)
- `GET /health` — Health check
- `GET /schema` — Action/Observation JSON schemas
- `WebSocket /ws` — Persistent connection for the agent

### EnvironmentMetadata (get_metadata)

Every OpenEnv environment has a `get_metadata()` method that returns structured information about the environment. The default implementation returns just the class name; gym authors override it to provide richer data.

```python
def get_metadata(self) -> EnvironmentMetadata:
    return EnvironmentMetadata(
        name="inventory_env",
        description="Inventory Management — 10 MCP tools ...",
        version="0.5.0",
        author="RL Gyms Team",
        readme_content=open("README.md").read(),  # optional, full README
        documentation_url="inventory/README.md",   # optional, docs link
    )
```

`create_app()` automatically exposes this as `GET /metadata` on the OpenEnv server. This is useful for:

- **AutoEnv discovery** — `AutoEnv.get_env_info()` returns package-level info, while `/metadata` returns runtime info from the actual environment instance
- **Evaluation logging** — `run_eval.py` fetches `/metadata` before each run and embeds the gym version in results markdown and trajectory JSON, so you always know which version of the gym produced which scores
- **Web UI** — the auto-generated OpenAPI docs at `/docs` display the metadata

Available fields:

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Environment identifier |
| `description` | `str` | What the environment does |
| `version` | `str` (optional) | Semantic version |
| `author` | `str` (optional) | Who built it |
| `readme_content` | `str` (optional) | Full README text |
| `documentation_url` | `str` (optional) | Link to docs |

### MCPToolClient

The low-level client for connecting to OpenEnv servers. In practice you don't instantiate this directly — **AutoEnv handles it** (see below).

```python
from openenv.core.mcp_client import MCPToolClient

env = MCPToolClient(base_url="http://localhost:9000")
env.reset()
tools = env.list_tools()           # discover available tools
result = env.call_tool("do_something", param="value")
```

### AutoEnv (Auto-Discovery)

`AutoEnv` is OpenEnv's auto-discovery system. Instead of manually importing client classes and specifying URLs, you just:

```python
from openenv import AutoEnv

# Discover and connect in one call
env = AutoEnv.from_env("inventory", base_url="http://localhost:9000")
env.reset()
tools = env.list_tools()
```

AutoEnv works by scanning pip-installed `openenv-*` packages. When you `pip install -e inventory/`, AutoEnv can find the gym's `openenv.yaml` manifest and `client.py` module, then:
1. Imports `InventoryEnv` from `inventory.client`
2. Creates an instance with the given `base_url`
3. Returns a fully typed client (with `InventoryAction` and `InventoryObservation` aliases)

To make a gym discoverable by AutoEnv:
1. It must be pip-installable (`pyproject.toml` with proper package config)
2. It must include `openenv.yaml` in its package data
3. `client.py` must export `<Name>Env`, `<Name>Action`, `<Name>Observation`

Related discovery helpers:
- `AutoEnv.list_environments()` — list all discovered gyms
- `AutoEnv.get_env_info(name)` — get metadata for a specific gym
- `AutoAction.from_env(name)` — get the Action type for a gym

### Action Types

OpenEnv uses a discriminated union for MCP actions:

- **ListToolsAction** — agent wants to see available tools
- **CallToolAction** — agent wants to execute a specific tool with arguments

Both are sent through the same `step()` channel. The server routes them automatically.

### Observation Types

After each action, the agent receives an observation:

- **CallToolObservation** — result of a tool call (includes `result`, `error`, `tool_name`)
- **Observation** — generic observation (used for resets, fallbacks)

### Concurrent Sessions

OpenEnv supports running multiple agents against the same server simultaneously. An environment class declares this by setting:

```python
class InventoryEnvironment(MCPEnvironment):
    SUPPORTS_CONCURRENT_SESSIONS: bool = True
```

When enabled, `create_app()` with `max_concurrent_envs=None` allows the server to create **separate `MCPEnvironment` instances** for each WebSocket connection. Each instance has its own state, its own HTTP client, and (for API-based gyms) its own isolated database.

For the Inventory gym, session isolation works via:
1. **Environment creates session** — `reset()` generates a UUID, calls `POST /sessions?session_id=<uuid>` to create an isolated SQLite DB
2. **Environment routes calls** — All HTTP requests include `X-Session-ID: <uuid>` header
3. **API routes to session DB** — The `get_db()` dependency reads the header and returns a session-scoped database connection
4. **Cleanup on close** — The environment calls `DELETE /sessions/<uuid>` to delete the session DB file

This allows `run_eval.py --parallel N` to evaluate N models simultaneously against one Docker container.

### Transforms

OpenEnv has a transform pipeline that can process observations before they reach the agent. We use this for **per-step reward calculation** — a transform inspects each tool call result and assigns a reward score. See [reward-system.md](reward-system.md) for details.

## Environment Types

OpenEnv supports two patterns for defining environments:

### Gymnasium-Style (typed actions)

Used for simple environments with a fixed action space (chess moves, game actions):

```python
from openenv.core.env_server.interfaces import Environment

class ChessEnv(Environment):
    def step(self, action: ChessAction) -> ChessObservation:
        # fixed action type
        ...
```

### MCP-Tool-Style (dynamic tools)

Used for complex environments with multiple operations (APIs, browsers, databases):

```python
from openenv.core.env_server.mcp_environment import MCPEnvironment
from fastmcp import FastMCP

class InventoryEnv(MCPEnvironment):
    def __init__(self):
        mcp = FastMCP("inventory")

        @mcp.tool()
        def create_product(name: str, price: float) -> dict: ...

        @mcp.tool()
        def create_order(items: list) -> dict: ...

        super().__init__(mcp)  # dynamic tool discovery
```

**This repository uses the MCP-tool pattern** for all gyms because the environments wrap real APIs with multiple operations.

## OpenEnv CLI

OpenEnv provides CLI commands for the full lifecycle:

| Command | Purpose |
|---------|---------|
| `openenv init <name>` | Scaffold a new environment (generates all required files) |
| `openenv validate <path>` | Check if the environment meets deployment requirements |
| `openenv build <path>` | Build a Docker image for the environment |

### What `openenv validate` checks

- `pyproject.toml` exists with `openenv-core` dependency and `server` entry point
- `uv.lock` exists (dependency lock file)
- `server/app.py` exists with a callable `main()` function
- `openenv.yaml` exists with manifest info

### What `openenv init` generates

```
my_gym/
├── __init__.py                     # Package exports
├── client.py                       # Client class (EnvClient or MCPToolClient)
├── models.py                       # Action/Observation models (typed pattern only)
├── openenv.yaml                    # Environment manifest
├── pyproject.toml                  # Dependencies & entry points
├── README.md                       # Documentation
├── uv.lock                         # Lock file (auto-generated)
└── server/
    ├── __init__.py
    ├── app.py                      # create_app() wiring
    ├── <name>_environment.py       # Environment class
    ├── Dockerfile                  # Docker build
    └── requirements.txt            # (redundant with pyproject.toml)
```

The default template uses the Gymnasium-style pattern. For MCP-tool-style, you customize the scaffold after generation — see [creating-a-new-gym.md](creating-a-new-gym.md).

## How This Repository Uses OpenEnv

```
┌────────────────────────────────────────────────────────────────────────┐
│                          This Repository                               │
│                                                                        │
│   run_eval.py                                                          │
│       │                                                                │
│       ├── AgentRunner (agent/runner.py)                                │
│       │      Connects LLM ↔ OpenEnv via MCPToolClient                 │
│       │                                                                │
│       ├── RewardCalculator (rewards/base.py)                          │
│       │      Episode-level scoring (custom mode)                      │
│       │                                                                │
│       ├── StepRewardTransform (rewards/transforms/)                   │
│       │      Per-step scoring via OpenEnv transforms (openenv mode)   │
│       │                                                                │
│       └── GYM_REGISTRY                                                │
│              Maps gym names → scenarios, checkers, transforms          │
│                                                                        │
│   inventory/                  ← Gym: real API + OpenEnv server        │
│   payment-gateway/            ← Gym: Payment Gateway (planned)        │
│                                                                        │
│   scenarios/                  ← What the agent is asked to do         │
│   rewards/                    ← How the agent is scored               │
│   results/                    ← Evaluation results (markdown)         │
│   trajectories/               ← Detailed run logs (JSON)             │
└────────────────────────────────────────────────────────────────────────┘
```

The evaluation flow:

1. **Install the gym** — `pip install -e inventory/` (one-time, enables AutoEnv discovery)
2. **Start Docker** — `docker run -d -p 8000:8000 -p 9000:9000 openenv-inventory`
3. **Run `run_eval.py`** — AutoEnv discovers the gym, auto-derives port from `openenv.yaml`, connects `AgentRunner` via `AutoEnv.from_env()`
4. **For each scenario**: Agent resets env → discovers tools → reasons with LLM → calls tools → gets observations → repeat until max steps
5. **Score**: Ground truth checked against real database; per-step or episode-level reward calculated
6. **Save**: Results to markdown, trajectories to JSON

For parallel evaluation (`--parallel N`), step 3 creates N independent AutoEnv clients, each with its own session-scoped database, and runs them concurrently via thread pool.
