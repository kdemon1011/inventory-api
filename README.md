# RL Gyms — OpenEnv Environments

A collection of reinforcement learning environments built on Meta's [OpenEnv](https://github.com/meta-pytorch/OpenEnv) framework. Each gym wraps a real API/tool as an MCP-based environment that AI agents can interact with through the standard `reset → step → observe` protocol.

The LLM **never calls tools directly** — it connects to OpenEnv, discovers available tools via `list_tools()`, and the agent runner routes each decision through `env.step()`. OpenEnv handles the actual execution.

## Setup

```bash
pip install -r requirements.txt

# Install each gym for AutoEnv auto-discovery
pip install -e inventory/
```

Add API keys to the root `.env`:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Gyms

| Gym | Type | Description | README |
|---|---|---|---|
| `inventory/` | API-based (two-process) | Inventory management — products + orders CRUD | [`inventory/README.md`](inventory/README.md) |
| `inventory_clone/` | In-memory (single-process) | Demo scaffold via `openenv init` | [`inventory_clone/README.md`](inventory_clone/README.md) |

Each gym has its own README with detailed architecture, running instructions, tools, scenarios, and reward examples.

## Quick Start

```bash
# 1. Install the gym for AutoEnv discovery (one-time)
pip install -e inventory/

# 2. Build and start Docker container
cd inventory && docker build -t openenv-inventory . && cd ..
docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory

# 3. Run an evaluation (AutoEnv discovers and connects automatically)
python run_eval.py --gym inventory --model gpt-4o --save --trajectory

# 3b. Or run multiple models in parallel (concurrent sessions)
python run_eval.py --gym inventory --model gpt-4o-mini,gpt-4o,claude-sonnet-4-6 --parallel 3 --save --trajectory

# 4. Stop
docker stop inventory && docker rm inventory
```

All gym connections use **AutoEnv auto-discovery** — no manual URLs needed. `run_eval.py` discovers the gym from its pip-installed package, reads the port from `openenv.yaml`, and connects via `AutoEnv.from_env()`.

Parallel mode (`--parallel N`) runs multiple models simultaneously against a **single Docker container**, each with its own isolated database session.

## Documentation

| Guide | Description |
|---|---|
| [How OpenEnv Works](docs/how-openenv-works.md) | OpenEnv architecture, key components, environment types, and how this repo uses them |
| [Repository Structure](docs/repository-structure.md) | What each folder does and how the pieces connect |
| [Running Evaluations](docs/running-evaluations.md) | CLI options, reward modes, trajectory logging, supported models |
| [Reward System](docs/reward-system.md) | Custom vs OpenEnv reward modes — formulas, comparison, and how to add rewards for a new gym |
| [Creating a New Gym](docs/creating-a-new-gym.md) | `openenv init` scaffolding, customization, and full registration checklist |
| [Docker Deployment](docs/docker-deployment.md) | Building and running gyms as Docker containers |
| [Multi-Gym Evaluation](docs/multi-gym-evaluation.md) | Running evaluations across multiple gyms with parallel models — full setup, commands, and output structure |