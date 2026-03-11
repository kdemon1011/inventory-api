# RL Gyms — OpenEnv Environments

A collection of reinforcement learning environments built on Meta's [OpenEnv](https://github.com/meta-pytorch/OpenEnv) framework. Each gym wraps a real API/tool as an MCP-based environment that AI agents can interact with through the standard `reset → step → observe` protocol.

## How It Works

```
┌─────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│  LLM            │         │  Agent Runner    │         │  OpenEnv Server  │
│  (GPT/Claude/   │ ──────► │  (gym-agnostic)  │ ──────► │  (per gym)       │
│   Ollama)       │         │                  │         │                  │
└─────────────────┘         └──────────────────┘         └──────────────────┘
   Decides WHAT              Sends to OpenEnv             Executes tools
   to do (reasoning)         via env.step()               (API / code / browser)
```

The LLM **never calls tools directly**. It connects to OpenEnv, discovers available tools via `list_tools()`, reasons about what to do, and the agent runner routes each decision through `env.step()`. OpenEnv handles the actual execution — whether that's an API call, code execution, or browser action.

## Repository Structure

```
├── agent/                     ← LLM Agent (gym-agnostic)
│   ├── llm.py                 ← LiteLLM wrapper (GPT, Claude, Ollama, etc.)
│   └── runner.py              ← Agent loop: LLM ↔ OpenEnv
│
├── inventory/                 ← Inventory Management gym
│   ├── main.py                ← FastAPI app (products + orders)
│   ├── server/                ← OpenEnv environment + server
│   ├── Dockerfile             ← Docker image for this gym
│   ├── client.py              ← MCPToolClient wrapper
│   ├── pyproject.toml         ← Package config (for openenv validate/build/uv run)
│   ├── openenv.yaml           ← Environment manifest
│   └── README.md              ← Gym-specific docs (how to run, tools, etc.)
│
├── rewards/                   ← Shared reward system
│   ├── base.py                ← RewardCalculator (gym-agnostic)
│   └── inventory_checks.py    ← Inventory ground truth verification
│
├── scenarios/                 ← Scenario definitions per gym
│   └── inventory.py           ← 10 inventory scenarios
│
├── results/                   ← Evaluation results (grouped by run)
│   └── inventory/             ← Results per gym
│       └── run_<timestamp>.md
│
├── trajectories/              ← Detailed run logs (grouped by run)
│   └── inventory/             ← Trajectories per gym
│       └── run_<timestamp>/   ← One JSON per model
│
├── tests/                     ← Manual integration tests
│   └── test_inventory_openenv.py
│
├── run_eval.py                ← CLI: evaluate LLM on a gym
├── .env                       ← API keys + model config
└── requirements.txt
```

## Setup

```bash
# Activate Python environment
source /path/to/your/venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### API Keys

Add your keys to the root `.env` file:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Running a Gym

Each gym can run via **Docker** (preferred) or **locally** using `uv run server`. Docker is the standard OpenEnv deployment method — it packages the backend and OpenEnv server into a single container.

For detailed setup and run instructions, see each gym's own README:

| Gym | Type | README | Status |
|---|---|---|---|
| `inventory/` | API-based | [`inventory/README.md`](inventory/README.md) | Active |

### Quick Start (Docker)

```bash
openenv build inventory/
docker run -d --name inventory -p 8000:8000 -p 9000:9000 openenv-inventory
```

### Validate

```bash
openenv validate inventory/
```

## Running an Evaluation

```bash
# Evaluate a model on all scenarios
python run_eval.py --gym inventory --model gpt-4o

# Save results + trajectory
python run_eval.py --gym inventory --model gpt-4o --save --trajectory

# Group runs together with a shared run ID
python run_eval.py --gym inventory --model gpt-4o --save --trajectory --run-id run_20260311_1830
python run_eval.py --gym inventory --model claude-sonnet-4-6 --save --trajectory --run-id run_20260311_1830
```

> Some models require `--temperature 1.0` (e.g., `gpt-5`, `gpt-5.4`, `o3-mini`, `o3-pro`, `o4-mini`).

### CLI Options

| Option | Default | Description |
|---|---|---|
| `--gym` | required | Which gym to evaluate (`inventory`, etc.) |
| `--model` | `gpt-4o` | LiteLLM model string |
| `--scenario` | all | Run a specific scenario by ID |
| `--openenv-url` | from gym config | OpenEnv server URL |
| `--api-url` | from gym config | API URL for ground truth checks |
| `--temperature` | `0.0` | LLM sampling temperature |
| `--max-tokens` | `1024` | Max tokens per LLM response |
| `--save` | off | Append results to `results/<gym>/<run_id>.md` |
| `--trajectory` | off | Save trajectory JSON to `trajectories/<gym>/<run_id>/` |
| `--run-id` | auto | Run ID for grouping results + trajectories |
| `-v` | off | Verbose/debug logging |

## Reward System

The reward calculator (`rewards/base.py`) is **gym-agnostic**. It computes an episode-level reward from 3 components:

| Component | Weight | What it checks |
|---|---|---|
| **Structural** | 0.25 | Did the agent call the right tools? (F1 + success rate) |
| **Ground Truth** | 0.60 | Does the database state match expected outcome? (source of truth) |
| **Efficiency** | 0.15 | Did the agent solve it in a reasonable number of steps? |

A **hallucination penalty** (-1.0) is applied if all tool calls "succeeded" but the database shows nothing actually happened.

## Trajectory Logging

When `--trajectory` is passed, a detailed JSON file is saved per model:

```
trajectories/<gym>/<run_id>/<model>.json
```

Each file contains run metadata, per-scenario step-by-step tool calls (arguments, results, timestamps), outcome checks, and reward breakdowns.

## Evaluation Results

Results are grouped by run: `results/<gym>/<run_id>.md`. See [`results/inventory/run_20260311_1830.md`](results/inventory/run_20260311_1830.md) for evaluation results across 16 LLM models.

## Adding a New Gym

1. Create a folder: `my_gym/` with your backend, OpenEnv environment (`server/`), `Dockerfile`, and client
2. Add `my_gym/pyproject.toml` — package config with `openenv-core` dependency and `server` entry point
3. Generate lock file: `cd my_gym && uv lock`
4. Add `rewards/my_gym_checks.py` — ground truth verification
5. Add `scenarios/my_gym.py` — scenario definitions
6. Register the gym in `run_eval.py` → `GYM_REGISTRY`
7. Add `my_gym/README.md` — detailed gym-specific docs (architecture, how to run, tools, etc.)
8. Validate: `openenv validate my_gym/`

The `agent/`, `rewards/base.py`, and `run_eval.py` work with ANY gym — no modifications needed.

## Supported Models

Any model supported by [LiteLLM](https://docs.litellm.ai/docs/providers):

| Provider | Example | Env Var |
|---|---|---|
| OpenAI | `gpt-4o`, `gpt-5.4`, `o3-pro` | `OPENAI_API_KEY` |
| Anthropic | `claude-opus-4-6`, `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| Ollama (local) | `ollama/llama3`, `ollama/mistral` | — (no key needed) |
| Google | `gemini/gemini-pro` | `GEMINI_API_KEY` |
| And 100+ more... | See LiteLLM docs | Varies |
