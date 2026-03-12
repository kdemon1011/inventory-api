# Repository Structure

This document explains how the repository is organized, what each folder does, and how the pieces connect.

## Top-Level Layout

```
├── agent/                     ← LLM Agent (gym-agnostic)
├── inventory/                 ← Gym: Inventory Management (Python/FastAPI)
├── payment-gateway/           ← Gym: Payment Gateway (Python + Node.js) [planned]
├── browser/                   ← Gym: Browser Automation (Node.js + React) [planned]
├── code-judge/                ← Gym: Code Judge (C++) [planned]
├── cloud-infra/               ← Gym: Cloud Infrastructure (Python) [planned]
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

The `AgentRunner` receives a pre-connected client (from AutoEnv discovery) and uses it to interact with any OpenEnv server. It doesn't know what gym it's talking to — it just discovers tools and calls them based on LLM reasoning.

## Gyms (`inventory/`, `payment-gateway/`, `browser/`, etc.)

Each gym is a self-contained folder that:
- Wraps a real system as an OpenEnv environment
- Passes `openenv validate`
- Can be deployed via Docker or run locally

### Gym: `inventory/` (full, two-process)

A real inventory management API (FastAPI + SQLite) wrapped as an OpenEnv environment.

```
inventory/
├── main.py                    ← FastAPI backend (products + orders CRUD + session endpoints)
├── database.py                ← SQLAlchemy engine + session-aware get_db()
├── session_manager.py         ← Per-session SQLite DB isolation for concurrent evaluation
├── schemas.py                 ← Pydantic request/response models
├── services.py                ← Business logic (stock management, order totals)
├── .env                       ← Configuration (ports, DB URL, concurrency)
├── server/                    ← OpenEnv layer
│   ├── app.py                 ← create_app() with MCPAction union + max_concurrent_envs
│   └── inventory_environment.py ← MCPEnvironment with 10 tools + get_session_info
├── client.py                  ← MCPToolClient + AutoEnv type aliases
├── Dockerfile                 ← Docker image (runs both API + OpenEnv server)
├── pyproject.toml             ← Dependencies + entry point
├── openenv.yaml               ← OpenEnv manifest
└── README.md                  ← Gym-specific docs
```

Architecture: two processes inside one Docker container:
```
Port 8000: Inventory API (FastAPI + SQLite)  ← real business logic + session management
Port 9000: OpenEnv Server (MCPEnvironment)   ← agent-facing interface (concurrent sessions)
```

The OpenEnv environment's tools (e.g., `create_product`, `list_orders`) make HTTP calls to the API on port 8000. Concurrent sessions are supported — multiple agents can evaluate simultaneously with isolated databases.

### Planned Gyms

| Gym | Language | Ports | Status |
|-----|----------|-------|--------|
| `payment-gateway/` | Python (FastAPI) + Node.js (Stripe mock) | 8002 / 9002 | Planned |
| `browser/` | Node.js (Express) + React | 8003 / 9003 | Planned |
| `code-judge/` | C++ (judge engine + API) | 8004 / 9004 | Planned |
| `cloud-infra/` | Python (FastAPI + AWS/Jenkins mocks) | 8005 / 9005 | Planned |

All planned gyms follow the same structure as `inventory/` — see [Creating a New Gym](creating-a-new-gym.md).

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
├── __init__.py                ← Exports INVENTORY_SCENARIOS
└── inventory.py               ← 10 inventory scenarios (create product, place order, etc.)
```

> The `Scenario` dataclass itself lives in `rewards/base.py` — shared across all gyms.

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

The main entry point. Connects everything via AutoEnv:

```python
GYM_REGISTRY = {
    "inventory": {
        "scenarios_loader": ...,     # what to test
        "checker_factory": ...,      # how to verify ground truth
        "transform_factory": ...,    # per-step reward transform
        "default_api_url": ...,      # for ground truth checker (not OpenEnv)
    },
    # "payment_gateway": { ... },  # planned
    # "browser": { ... },           # planned
    # "code_judge": { ... },        # planned
    # "cloud_infra": { ... },       # planned
}
```

The OpenEnv base_url is **auto-derived** from the gym's `openenv.yaml` port — no hardcoded URLs needed.

Supports two execution modes:
- **Sequential** (default): One model at a time, backward-compatible
- **Parallel** (`--parallel N`): N models simultaneously, each with its own AutoEnv client and isolated DB session

To add a new gym: `pip install -e <gym>/` and add an entry to `GYM_REGISTRY` — the rest of the evaluation infrastructure (agent, scoring, saving) is shared.

## How the Pieces Connect

```
run_eval.py ──► GYM_REGISTRY["inventory"]
                    │
                    ├── scenarios_loader  → scenarios/inventory.py  → INVENTORY_SCENARIOS
                    │
                    ├── checker_factory   → rewards/inventory_checks.py → InventoryChecker
                    │
                    ├── transform_factory → rewards/transforms/inventory.py → InventoryStepTransform
                    │
                    └── base_url ──► AutoEnv.from_env("inventory", base_url=...)
                                         │
                                         ▼ (auto-discovers from pip-installed package)
                                    inventory.client.InventoryEnv
                                         │
                                         ▼ (connects to OpenEnv server)
                                    inventory/server/app.py → InventoryEnvironment
                                         │
                                         ▼
                                    inventory/main.py (FastAPI, port 8000)
```
