# Repository Structure

This document explains how the repository is organized, what each folder does, and how the pieces connect.

## Top-Level Layout

```
├── agent/                     ← LLM Agent (gym-agnostic)
├── inventory/                 ← Gym: Inventory Management (full, two-process)
├── inventory_clone/           ← Gym: Demo scaffold (single-process, in-memory)
├── rewards/                   ← Shared reward system (both custom and OpenEnv)
├── scenarios/                 ← Scenario definitions per gym
├── results/                   ← Evaluation results (grouped by run)
├── trajectories/              ← Detailed step-by-step logs (grouped by run)
├── docs/                      ← Documentation
├── tests/                     ← Integration tests
├── run_eval.py                ← CLI entry point: evaluate LLM on a gym
├── requirements.txt           ← Root Python dependencies
└── .env                       ← API keys + model config
```

## Agent (`agent/`)

The agent is **gym-agnostic** — it works with any gym without modification.

| File | Purpose |
|------|---------|
| `agent/llm.py` | LiteLLM wrapper — unified interface for GPT, Claude, Ollama, Gemini, etc. |
| `agent/runner.py` | Agent loop: resets env → LLM reasons → sends tool calls → observes → repeat |

The `AgentRunner` connects to any OpenEnv server via `MCPToolClient`. It doesn't know what gym it's talking to — it just discovers tools and calls them based on LLM reasoning.

## Gyms (`inventory/`, `inventory_clone/`, etc.)

Each gym is a self-contained folder that:
- Wraps a real system as an OpenEnv environment
- Passes `openenv validate`
- Can be deployed via Docker or run locally

### Gym: `inventory/` (full, two-process)

A real inventory management API (FastAPI + SQLite) wrapped as an OpenEnv environment.

```
inventory/
├── main.py                    ← FastAPI backend (products + orders CRUD)
├── database.py                ← SQLAlchemy models + SQLite
├── schemas.py                 ← Pydantic request/response models
├── services.py                ← Business logic (stock management, order totals)
├── config.py                  ← Configuration (ports, DB path)
├── server/                    ← OpenEnv layer
│   ├── app.py                 ← create_app() with MCPAction union
│   └── inventory_environment.py ← MCPEnvironment with 10 tools (calls the real API)
├── client.py                  ← MCPToolClient wrapper
├── Dockerfile                 ← Docker image (runs both API + OpenEnv server)
├── pyproject.toml             ← Dependencies + entry point
├── openenv.yaml               ← OpenEnv manifest
└── README.md                  ← Gym-specific docs
```

Architecture: two processes inside one Docker container:
```
Port 8000: Inventory API (FastAPI + SQLite)  ← real business logic
Port 9000: OpenEnv Server (MCPEnvironment)   ← agent-facing interface
```

The OpenEnv environment's tools (e.g., `create_product`, `list_orders`) make HTTP calls to the API on port 8000.

### Gym: `inventory_clone/` (demo, single-process)

A simplified clone scaffolded via `openenv init inventory_clone`. Uses in-memory storage instead of a real database. Demonstrates what a new gym looks like after scaffolding.

```
inventory_clone/
├── server/
│   ├── app.py                 ← create_app() wiring
│   ├── inventory_clone_environment.py ← MCPEnvironment with 7 tools (in-memory dicts)
│   ├── Dockerfile             ← Single-process Docker image
│   └── __init__.py
├── client.py                  ← MCPToolClient wrapper
├── __init__.py                ← Package init
├── pyproject.toml             ← Dependencies
├── openenv.yaml               ← Manifest
├── uv.lock                    ← Lock file
└── README.md
```

Architecture: single process, no separate API:
```
Port 9000: OpenEnv Server (MCPEnvironment with in-memory data)
```

## Rewards (`rewards/`)

Two reward systems, selectable via `--reward-mode`:

```
rewards/
├── base.py                    ← RewardCalculator (episode-level, custom mode)
│                                 RewardBreakdown (shared data class)
├── inventory_checks.py        ← Ground truth verification (queries DB after episode)
└── transforms/                ← OpenEnv-native per-step rewards (openenv mode)
    ├── __init__.py
    ├── base.py                ← StepRewardTransform + OpenEnvRewardCalculator
    └── inventory.py           ← InventoryStepTransform (gym-specific scoring)
```

See [reward-system.md](reward-system.md) for how each mode works.

## Scenarios (`scenarios/`)

Each gym has scenario definitions — structured prompts that tell the agent what to do:

```
scenarios/
├── base.py                    ← Scenario dataclass (id, prompt, expected_tools, outcome_checks)
└── inventory.py               ← 10 inventory scenarios (create product, place order, etc.)
```

A scenario includes:
- **`prompt`**: Natural language instruction for the LLM
- **`expected_tools`**: Which tools should be called (for custom reward scoring)
- **`outcome_checks`**: Ground truth checks to run after the episode (e.g., "product with SKU X exists")
- **`max_steps`**: Step budget

## Results & Trajectories

```
results/
└── inventory/
    ├── run_20260311_1830.md              ← Custom rewards run
    ├── run_20260312_0100.md              ← OpenEnv transform rewards run
    └── comparison_custom_vs_openenv.md   ← Side-by-side analysis

trajectories/
└── inventory/
    ├── run_20260311_1830/                ← One JSON per model
    │   ├── claude-opus-4-20250514.json
    │   ├── gpt-5.4.json
    │   └── ...
    └── run_20260312_0100/
        ├── claude-opus-4-20250514.json
        └── ...
```

- **Results**: Markdown tables with per-scenario and aggregate scores
- **Trajectories**: Step-by-step JSON logs (tool name, arguments, result, timing, reward)

## Evaluation CLI (`run_eval.py`)

The main entry point. Connects everything:

```python
GYM_REGISTRY = {
    "inventory": {
        "scenarios_loader": ...,     # what to test
        "checker_factory": ...,      # how to verify ground truth
        "transform_factory": ...,    # per-step reward transform
        "default_openenv_url": ...,  # where the gym is running
        "default_api_url": ...,      # where the backend API is
    },
    "inventory_clone": { ... },
}
```

To add a new gym, you add an entry to `GYM_REGISTRY` — the rest of the evaluation infrastructure (agent, scoring, saving) is shared.

## How the Pieces Connect

```
run_eval.py ──► GYM_REGISTRY["inventory"]
                    │
                    ├── scenarios_loader → scenarios/inventory.py  → INVENTORY_SCENARIOS
                    │
                    ├── checker_factory  → rewards/inventory_checks.py → InventoryChecker
                    │
                    ├── transform_factory → rewards/transforms/inventory.py → InventoryStepTransform
                    │
                    └── openenv_url     → MCPToolClient("http://localhost:9000")
                                              │
                                              ▼
                                         inventory/server/app.py → InventoryEnvironment
                                              │
                                              ▼
                                         inventory/main.py (FastAPI, port 8000)
```
