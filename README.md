# RL Gyms — OpenEnv Environments

A collection of reinforcement learning environments built on Meta's [OpenEnv](https://github.com/meta-pytorch/OpenEnv) framework. Each gym wraps a real API/tool as an MCP-based environment that AI agents can interact with through the standard `reset → step → observe` protocol.

The LLM **never calls tools directly** — it connects to OpenEnv, discovers available tools via `list_tools()`, and the agent runner routes each decision through `env.step()`. OpenEnv handles the actual execution.

## Setup

```bash
pip install -r requirements.txt
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
# 1. Start a gym (Docker)
cd inventory && docker build -t openenv-inventory -f Dockerfile . && cd ..
docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory

# 2. Run an evaluation
python run_eval.py --gym inventory --model gpt-4o --save --trajectory

# 3. Stop
docker stop inventory && docker rm inventory
```

## Documentation

| Guide | Description |
|---|---|
| [How OpenEnv Works](docs/how-openenv-works.md) | OpenEnv architecture, key components, environment types, and how this repo uses them |
| [Repository Structure](docs/repository-structure.md) | What each folder does and how the pieces connect |
| [Running Evaluations](docs/running-evaluations.md) | CLI options, reward modes, trajectory logging, supported models |
| [Reward System](docs/reward-system.md) | Custom vs OpenEnv reward modes — formulas, comparison, and how to add rewards for a new gym |
| [Creating a New Gym](docs/creating-a-new-gym.md) | `openenv init` scaffolding, customization, and full registration checklist |
| [Docker Deployment](docs/docker-deployment.md) | Building and running gyms as Docker containers |
