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
│   ├── base.py                ← RewardCalculator (gym-agnostic, episode-level)
│   ├── inventory_checks.py    ← Inventory ground truth verification
│   └── transforms/            ← OpenEnv-native per-step rewards
│       ├── base.py            ← StepRewardTransform + OpenEnvRewardCalculator
│       └── inventory.py       ← Inventory-specific step transform
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

# Use OpenEnv per-step reward mode (instead of default custom episode-level)
python run_eval.py --gym inventory --model gpt-4o --reward-mode openenv --save --trajectory

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
| `--reward-mode` | `custom` | `custom` (episode-level) or `openenv` (per-step transform) |
| `-v` | off | Verbose/debug logging |

## Reward System

Two reward modes are available via `--reward-mode`. Both share the same ground truth verification and hallucination penalty — the difference is how per-step performance is scored.

### Custom Mode (default: `--reward-mode custom`)

Episode-level reward from `rewards/base.py`. Evaluates the agent **after the episode ends**, looking at the full picture.

| Component | Weight | What it checks | How it's calculated |
|---|---|---|---|
| **Structural** | 0.25 | Did the agent call the right tools without errors? | `0.6 × F1(expected_tools, used_tools) + 0.4 × success_rate` |
| **Ground Truth** | 0.60 | Does the database state match expected outcome? | `passed_checks / total_checks` — queries DB after episode |
| **Efficiency** | 0.15 | Did the agent solve it in a reasonable number of steps? | `min(expected_steps / actual_steps, 1.0)` |
| **Penalty** | -1.0 | Hallucination: tools say success but DB disagrees | Applied when ALL steps succeed AND zero ground truth checks pass |

**Total** = `0.25 × structural + 0.60 × ground_truth + 0.15 × efficiency + penalty`, clamped to [-1.0, 1.0]

### OpenEnv Mode (`--reward-mode openenv`)

Per-step reward from `rewards/transforms/` combined with ground truth. Evaluates each tool call **as it happens** using OpenEnv's native Transform system.

| Component | Weight | What it checks | How it's calculated |
|---|---|---|---|
| **Step Rewards** | 0.40 | Did each tool call produce a quality result? | Average per-step reward, normalized from [-0.5, 1.0] → [0, 1] |
| **Ground Truth** | 0.60 | Does the database state match expected outcome? | `passed_checks / total_checks` — same DB verification as custom |
| **Efficiency** | — | Not applicable | Always 0.0 (transform has no access to expected step count) |
| **Penalty** | -1.0 | Hallucination: step rewards positive but DB disagrees | Applied when ALL step rewards > 0 AND zero ground truth checks pass |

**Total** = `0.40 × step_score + 0.60 × ground_truth + penalty`, clamped to [-1.0, 1.0]

#### How per-step rewards work

Each gym defines a **Transform** (subclass of `StepRewardTransform`) that inspects the raw observation after each tool call and assigns a reward. The transform sees **one observation at a time** — it does not know the scenario, expected tools, or step count.

The per-step reward values are gym-specific. For the Inventory gym (`rewards/transforms/inventory.py`):

| Result type | Per-step reward | Example |
|---|---|---|
| Entity created/retrieved (dict with `id`) | **1.0** | `create_product` returns `{"id": 1, "name": "..."}` |
| Listed entities (non-empty list) | **0.8** | `list_products` returns `[{...}, {...}]` |
| Valid but empty/minimal result | **0.5** | `search_products` returns `[]` |
| Error (API returned error) | **-0.5** | Invalid arguments, server error |
| Non-tool observation | **0.0** | System messages, resets |

The raw average of all step rewards is **normalized** to [0, 1] range: `step_score = (avg + 0.5) / 1.5`. This normalized value is what appears as "Structural" in the results table (reusing the same display column for compatibility).

#### Worked example

Scenario `product_and_order` with 2 steps:

| Step | Tool | Result | Per-step reward |
|---|---|---|---|
| 1 | `create_product` | `{"id": 1, "name": "..."}` | 1.0 |
| 2 | `create_order` | `{"id": 1, "items": [...]}` | 1.0 |

- Step score: avg = 1.0, normalized = (1.0 + 0.5) / 1.5 = **1.00**
- Ground truth: 2 of 3 checks pass → **0.67**
- Total: 0.40 × 1.00 + 0.60 × 0.67 = **0.80**

### Hallucination Penalty (both modes)

A **-1.0 penalty** is applied when all tool calls appear successful but the database shows nothing actually happened. This is the strongest signal of hallucination — the model "thought" it did everything correctly, but the ground truth says otherwise.

### Custom vs OpenEnv — What Each Measures

| Check | Custom | OpenEnv | Why the difference |
|---|:---:|:---:|---|
| Tool selection (right tools called?) | ✅ F1 score | ❌ | Transform sees one observation at a time — no episode context |
| Execution success rate | ✅ Boolean | ✅ Graded | Custom: pass/fail. OpenEnv: 1.0/0.8/0.5/-0.5 based on result quality |
| Result content quality | ❌ | ✅ | Transform inspects the actual response structure (dict with id, list, etc.) |
| Efficiency (step count) | ✅ | ❌ | Transform has no access to expected step count or scenario |
| Ground truth (DB verification) | ✅ (0.60) | ✅ (0.60) | Both query the actual database after the episode — identical logic |
| Hallucination penalty | ✅ (-1.0) | ✅ (-1.0) | Both: all tools "succeed" but DB shows nothing |

**Why two modes?** They measure different things. Custom asks *"did the agent follow the right plan?"* (tool selection + efficiency). OpenEnv asks *"did each step produce a quality result?"* (per-step result validation). A model can score high on one and low on the other — running both gives a fuller picture.

**Why can't OpenEnv transforms check tool selection or efficiency?** The transform receives a single `Observation` after each step. It has no access to the scenario definition, expected tools, or total step count. These are episode-level metrics that require the full context — which only the custom `RewardCalculator` has.

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
5. Add `rewards/transforms/my_gym.py` — per-step reward transform (for `--reward-mode openenv`)
6. Add `scenarios/my_gym.py` — scenario definitions
7. Register the gym in `run_eval.py` → `GYM_REGISTRY` (scenarios, checker, **transform**)
8. Add `my_gym/README.md` — detailed gym-specific docs (architecture, how to run, tools, etc.)
9. Validate: `openenv validate my_gym/`

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
