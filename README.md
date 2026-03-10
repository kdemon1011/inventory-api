# RL Gyms — OpenEnv Environments

A collection of reinforcement learning environments built on Meta's [OpenEnv](https://github.com/meta-pytorch/OpenEnv) framework. Each gym wraps a real API as an MCP-based environment that AI agents can interact with through the standard `reset → step → observe` protocol.

## How It Works

```
┌─────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│  LLM            │         │  Agent Runner     │         │  OpenEnv Server  │
│  (GPT/Claude/   │ ──────► │  (gym-agnostic)   │ ──────► │  (per gym)       │
│   Ollama)       │         │                   │         │                  │
└─────────────────┘         └──────────────────┘         └──────────────────┘
   Decides WHAT              Sends to OpenEnv              Routes to real API
   to do (reasoning)         via env.step()                (database, etc.)
```

The LLM **never calls tools directly**. It connects to OpenEnv, discovers available tools via `list_tools()`, reasons about what to do, and the agent runner routes each decision through `env.step()`. OpenEnv handles the actual API calls.

## Repository Structure

```
├── agent/                     ← LLM Agent (gym-agnostic)
│   ├── llm.py                 ← LiteLLM wrapper (GPT, Claude, Ollama, etc.)
│   └── runner.py              ← Agent loop: LLM ↔ OpenEnv
│
├── inventory/                 ← Inventory Management gym
│   ├── main.py                ← FastAPI app (products + orders)
│   ├── server/                ← OpenEnv environment + server
│   ├── client.py              ← MCPToolClient wrapper
│   └── README.md              ← Gym-specific docs
│
├── rewards/                   ← Shared reward system
│   ├── base.py                ← RewardCalculator (gym-agnostic)
│   └── inventory_checks.py    ← Inventory ground truth verification
│
├── scenarios/                 ← Scenario definitions per gym
│   └── inventory.py           ← Inventory scenarios
│
├── tests/                     ← Manual integration tests (debugging)
│   └── test_inventory_openenv.py
│
├── run_eval.py                ← CLI entry point: evaluate LLM on a gym
├── .env                       ← API keys + model config
└── requirements.txt
```

## Setup

```bash
# Activate Python environment
source /home/kdemon/Clients/personal_python_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### API Keys

Add your keys to the root `.env` file:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

For local models (Ollama), no API key needed — just install and run Ollama:
```bash
ollama serve
ollama pull llama3
```

## Running an Evaluation

### 1. Start the gym servers

Each gym needs two processes: the API and the OpenEnv server.

```bash
# Terminal 1 — Inventory API (port 8000)
cd inventory && python main.py

# Terminal 2 — OpenEnv server (port 9000)
cd inventory && python server/app.py
```

### 2. Run the LLM evaluation

```bash
# Evaluate with OpenAI GPT-4o
python run_eval.py --gym inventory --model gpt-4o

# Evaluate with Anthropic Claude
python run_eval.py --gym inventory --model claude-sonnet-4-20250514

# Evaluate with local Ollama model
python run_eval.py --gym inventory --model ollama/llama3

# Run a specific scenario only
python run_eval.py --gym inventory --model gpt-4o --scenario create_product

# Verbose mode (see LLM reasoning)
python run_eval.py --gym inventory --model gpt-4o -v
```

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
| `-v` | off | Verbose/debug logging |

## Reward System

The reward calculator (`rewards/base.py`) is **gym-agnostic**. It computes an episode-level reward from 3 components:

| Component | Weight | What it checks |
|---|---|---|
| **Structural** | 0.25 | Did the agent call the right tools? (F1 + success rate) |
| **Ground Truth** | 0.60 | Does the database state match expected outcome? (source of truth) |
| **Efficiency** | 0.15 | Did the agent solve it in a reasonable number of steps? |

A **hallucination penalty** (-1.0) is applied if all tool calls "succeeded" but the database shows nothing actually happened.

## Adding a New Gym

1. Create a folder: `my_gym/` with your API, OpenEnv environment, and client
2. Add `rewards/my_gym_checks.py` — ground truth verification
3. Add `scenarios/my_gym.py` — scenario definitions
4. Register the gym in `run_eval.py` → `GYM_REGISTRY`
5. Add `my_gym/README.md` — gym-specific docs

The `agent/`, `rewards/base.py`, and `run_eval.py` work with ANY gym — no modifications needed.

## Available Gyms

| Gym | Description | Tools | Status |
|---|---|---|---|
| `inventory/` | Inventory management (products + orders) | 10 | ✅ Active |

## Supported Models

Any model supported by [LiteLLM](https://docs.litellm.ai/docs/providers):

| Provider | Example | Env Var |
|---|---|---|
| OpenAI | `gpt-4o`, `gpt-4-turbo` | `OPENAI_API_KEY` |
| Anthropic | `claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |
| Ollama (local) | `ollama/llama3`, `ollama/mistral` | — (no key needed) |
| Google | `gemini/gemini-pro` | `GEMINI_API_KEY` |
| And 100+ more... | See LiteLLM docs | Varies |
