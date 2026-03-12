# Multi-Gym Evaluation Guide

How to run evaluations across multiple gyms with multiple models — from a single gym test to full-scale parallel evaluation across your entire gym collection.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Your Machine / CI Server                          │
│                                                                             │
│  Docker Containers (one per gym, each on its own ports):                    │
│                                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │  inventory           │  │  math                │  │  devops              │  │
│  │  API: 8000           │  │  (no API, in-memory) │  │  API: 8003           │  │
│  │  OpenEnv: 9000       │  │  OpenEnv: 9002       │  │  OpenEnv: 9003       │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
│         ▲                         ▲                         ▲                │
│         │                         │                         │                │
│  ┌──────┴──────┐           ┌──────┴──────┐           ┌──────┴──────┐        │
│  │ run_eval.py │           │ run_eval.py │           │ run_eval.py │        │
│  │ --gym inv   │           │ --gym math  │           │ --gym devops│        │
│  │ --parallel 3│           │ --parallel 2│           │ --parallel 2│        │
│  └─────────────┘           └─────────────┘           └─────────────┘        │
│   Terminal 1                Terminal 2                Terminal 3              │
└─────────────────────────────────────────────────────────────────────────────┘
```

Key rules:
- **One Docker container per gym** (each gym has its own OpenEnv server on a unique port)
- **One `run_eval.py` invocation per gym** (use `--gym` flag)
- **Multiple models per gym** are supported via `--parallel N` within a single invocation
- **Multiple gyms** run simultaneously by launching `run_eval.py` in separate terminals

## Step-by-Step: Setting Up 3 Gyms

### 1. Install each gym for AutoEnv discovery (one-time)

```bash
# From the repo root
pip install -e inventory/
pip install -e math/
pip install -e devops/
```

Verify all gyms are discoverable:
```bash
python -c "from openenv import AutoEnv; print(AutoEnv.list_environments())"
# Should list: inventory_env, math_env, devops_env
```

### 2. Build Docker images (one-time, or after code changes)

```bash
# Build each gym's image
cd inventory && docker build -t openenv-inventory . && cd ..
cd math && docker build -t openenv-math . && cd ..
cd devops && docker build -t openenv-devops . && cd ..
```

### 3. Start all containers

Each gym runs on its own ports (defined in its `openenv.yaml` and `.env`):

```bash
# Inventory — two-process (API + OpenEnv)
docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory

# Math — single-process (in-memory, OpenEnv only)
docker run -d --name math -p 9002:9002 openenv-math

# DevOps — two-process (API + OpenEnv)
docker run -d --name devops -p 8003:8003 -p 9003:9003 openenv-devops
```

Verify all are healthy:
```bash
curl http://localhost:9000/health    # inventory
curl http://localhost:9000/metadata  # inventory metadata (name, version)
curl http://localhost:9002/health    # math
curl http://localhost:9003/health    # devops
```

### 4. Register each gym in `GYM_REGISTRY`

In `run_eval.py`, each gym needs an entry:

```python
GYM_REGISTRY = {
    "inventory": {
        "scenarios_loader": lambda: _load_inventory_scenarios(),
        "checker_factory": lambda api_url, session_id=None: _create_inventory_checker(api_url, session_id),
        "transform_factory": lambda: _create_inventory_transform(),
        "default_api_url": "http://localhost:8000",
    },
    "math": {
        "scenarios_loader": lambda: _load_math_scenarios(),
        "checker_factory": lambda api_url, session_id=None: _create_math_checker(),
        "transform_factory": lambda: _create_math_transform(),
        "default_api_url": None,  # in-memory, no separate API
    },
    "devops": {
        "scenarios_loader": lambda: _load_devops_scenarios(),
        "checker_factory": lambda api_url, session_id=None: _create_devops_checker(api_url, session_id),
        "transform_factory": lambda: _create_devops_transform(),
        "default_api_url": "http://localhost:8003",
    },
}
```

No `base_url` or `openenv_url` needed — AutoEnv reads the port from each gym's `openenv.yaml`.

## Running Evaluations

### Single gym, single model

```bash
python run_eval.py --gym inventory --model gpt-4o --save --trajectory
```

### Single gym, multiple models in parallel

```bash
# 3 models, 3 parallel workers → all run simultaneously
python run_eval.py --gym inventory \
  --model gpt-4o-mini,gpt-4o,claude-sonnet-4-6 \
  --parallel 3 \
  --reward-mode openenv \
  --save --trajectory
```

How it works internally:
1. `run_eval.py` creates a thread pool with N workers
2. Each worker creates its **own AutoEnv client** → own WebSocket → own `MCPEnvironment` instance
3. Each `env.reset()` creates a **unique session ID** + isolated SQLite DB
4. All HTTP calls include `X-Session-ID` header → no cross-contamination
5. Ground truth checker is session-aware (queries the correct DB)
6. Session DBs are auto-cleaned when evaluation finishes

### Multiple gyms simultaneously (3 terminals)

Open 3 separate terminals and run each gym's evaluation:

**Terminal 1 — Inventory**
```bash
python run_eval.py --gym inventory \
  --model gpt-4o-mini,gpt-4o,claude-sonnet-4-6 \
  --parallel 3 \
  --reward-mode openenv \
  --save --trajectory
```

**Terminal 2 — Math**
```bash
python run_eval.py --gym math \
  --model gpt-4o-mini,gpt-4o \
  --parallel 2 \
  --reward-mode openenv \
  --save --trajectory
```

**Terminal 3 — DevOps**
```bash
python run_eval.py --gym devops \
  --model gpt-4o-mini,gpt-4o \
  --parallel 2 \
  --reward-mode openenv \
  --save --trajectory
```

Each `run_eval.py` talks to its own Docker container on its own port — they don't interfere.

### Full-scale example: 9 models across 3 gyms

```bash
# Terminal 1: Inventory (9 models, 3 at a time)
python run_eval.py --gym inventory \
  --model gpt-4o-mini,gpt-4o,gpt-5,gpt-5-mini,o3-mini,o3-pro,o4-mini,claude-sonnet-4-6,claude-opus-4-20250514 \
  --parallel 3 \
  --temperature 0.0 \
  --reward-mode openenv \
  --save --trajectory

# Terminal 2: Math (same 9 models)
python run_eval.py --gym math \
  --model gpt-4o-mini,gpt-4o,gpt-5,gpt-5-mini,o3-mini,o3-pro,o4-mini,claude-sonnet-4-6,claude-opus-4-20250514 \
  --parallel 3 \
  --reward-mode openenv \
  --save --trajectory

# Terminal 3: DevOps (same 9 models)
python run_eval.py --gym devops \
  --model gpt-4o-mini,gpt-4o,gpt-5,gpt-5-mini,o3-mini,o3-pro,o4-mini,claude-sonnet-4-6,claude-opus-4-20250514 \
  --parallel 3 \
  --reward-mode openenv \
  --save --trajectory
```

> **Note**: `--parallel 3` means 3 models run at the same time. With 9 models, it will process them in 3 batches of 3. Increase `--parallel` if your machine and API rate limits allow.

> **Note**: Some models (o3-mini, o3-pro, o4-mini, gpt-5, gpt-5-mini) require `--temperature 1.0`. If mixing models that need different temperatures, either run them in separate batches or use the default `0.0` (the agent runner handles provider-specific overrides).

## Output Structure

After running all 3 gyms, your repo will have:

```
results/
├── inventory/
│   └── run_20260312_2200.md          ← all 9 model scores for inventory
├── math/
│   └── run_20260312_2200.md          ← all 9 model scores for math
└── devops/
    └── run_20260312_2200.md          ← all 9 model scores for devops

trajectories/
├── inventory/
│   └── run_20260312_2200/
│       ├── gpt-4o-mini.json          ← step-by-step tool calls + rewards
│       ├── gpt-4o.json
│       ├── gpt-5.json
│       └── ... (9 files)
├── math/
│   └── run_20260312_2200/
│       ├── gpt-4o-mini.json
│       └── ... (9 files)
└── devops/
    └── run_20260312_2200/
        ├── gpt-4o-mini.json
        └── ... (9 files)
```

Each results markdown includes:
- Run ID, gym version (from `/metadata`), reward mode
- Per-model section with scenario-by-scenario breakdown
- Average reward per model

Each trajectory JSON includes:
- Run metadata (run_id, model, gym, gym_version, timestamp, reward_mode)
- Per-scenario: prompt, expected tools, step-by-step tool calls, results, rewards

## Port Conventions

Each gym uses a unique port range to avoid conflicts:

| Gym | API Port | OpenEnv Port | Docker Image |
|---|---|---|---|
| `inventory` | 8000 | 9000 | `openenv-inventory` |
| `inventory_clone` | — | 9001 | `openenv-inventory-clone` |
| `math` | — | 9002 | `openenv-math` |
| `devops` | 8003 | 9003 | `openenv-devops` |
| *(future gym)* | 800N | 900N | `openenv-<name>` |

Ports are defined in each gym's `openenv.yaml` (for OpenEnv) and `.env` (for API). AutoEnv reads `openenv.yaml` automatically — no hardcoded ports in `run_eval.py`.

## Cleanup

After evaluation, stop and remove all containers:

```bash
docker stop inventory math devops
docker rm inventory math devops
```

Or for a fresh restart (clean databases):
```bash
docker stop inventory && docker rm inventory
docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory
```

## Quick Reference

| Task | Command |
|---|---|
| Evaluate 1 model on 1 gym | `python run_eval.py --gym inventory --model gpt-4o` |
| Evaluate 3 models in parallel on 1 gym | `python run_eval.py --gym inventory --model a,b,c --parallel 3` |
| Evaluate across 3 gyms | Run 3 separate `run_eval.py` commands in 3 terminals |
| Save results + trajectories | Add `--save --trajectory` |
| Use per-step rewards | Add `--reward-mode openenv` |
| Check gym metadata | `curl http://localhost:9000/metadata` |
| Reset a gym's DB | `docker stop <name> && docker rm <name> && docker run ...` |
| Verify AutoEnv discovery | `python -c "from openenv import AutoEnv; print(AutoEnv.list_environments())"` |

## FAQ

**Q: Can I run all 3 gyms from a single `run_eval.py` command?**
No. Each invocation handles one gym (`--gym inventory`). Run separate commands in separate terminals for multiple gyms. They don't conflict because each gym has its own Docker container and port.

**Q: Do I need multiple Docker containers for parallel models within one gym?**
No. One container handles all concurrent models. `--parallel 3` creates 3 isolated sessions inside the same container.

**Q: What if a model needs a different temperature?**
Run it separately: `python run_eval.py --gym inventory --model o3-pro --temperature 1.0 --save --trajectory`. Use the same `--run-id` to group results with other models.

**Q: How do I add a new gym?**
See [creating-a-new-gym.md](creating-a-new-gym.md) for the full process: `openenv init`, customize, Docker, pip install, register in `GYM_REGISTRY`.
