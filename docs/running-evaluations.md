# Running Evaluations

`run_eval.py` is the main CLI entry point. It connects an LLM agent to an OpenEnv gym, runs scenarios, scores the results, and optionally saves everything.

## Prerequisites

1. **API keys** in root `.env`:
   ```env
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   ```

2. **Gym running** — either via Docker or locally. See the gym's own README for how to start it:
   - [`inventory/README.md`](../inventory/README.md)
   - [`inventory_clone/README.md`](../inventory_clone/README.md)

3. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```

## Basic Usage

```bash
# Evaluate a model on all scenarios
python run_eval.py --gym inventory --model gpt-4o

# Save results to markdown + trajectory JSON
python run_eval.py --gym inventory --model gpt-4o --save --trajectory

# Use OpenEnv per-step reward mode
python run_eval.py --gym inventory --model gpt-4o --reward-mode openenv --save --trajectory

# Run a specific scenario only
python run_eval.py --gym inventory --model gpt-4o --scenario create_product

# Group multiple model runs under the same run ID
python run_eval.py --gym inventory --model gpt-4o --save --trajectory --run-id run_20260311_1830
python run_eval.py --gym inventory --model claude-sonnet-4-6 --save --trajectory --run-id run_20260311_1830
```

> Some models require `--temperature 1.0` (e.g., `gpt-5`, `gpt-5.4`, `o3-mini`, `o3-pro`, `o4-mini`).

## CLI Options

| Option | Default | Description |
|---|---|---|
| `--gym` | required | Which gym to evaluate (`inventory`, `inventory_clone`, etc.) |
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

## What Happens During an Evaluation

For each scenario:

1. **Reset** — `env.reset()` clears the environment state
2. **Discover** — Agent calls `list_tools()` to see available tools
3. **Reason** — LLM reads the scenario prompt + tool list and decides what to do
4. **Execute** — Agent sends `call_tool(...)` through OpenEnv
5. **Observe** — Agent receives the result and reasons about the next step
6. **Repeat** — Steps 3–5 until the LLM signals done or max steps reached
7. **Score** — Ground truth is checked against the real database; reward is calculated

## Results

When `--save` is passed, results are appended to:
```
results/<gym>/<run_id>.md
```

Each model gets its own section in the file with a per-scenario breakdown table. Multiple models can be run under the same `--run-id` to build up a comparison.

Example: `results/inventory/run_20260311_1830.md`

## Trajectory Logging

When `--trajectory` is passed, a detailed JSON file is saved per model:
```
trajectories/<gym>/<run_id>/<model>.json
```

Each trajectory contains:
- Run metadata (run_id, model, gym, timestamp, temperature, reward_mode)
- Per-scenario step-by-step tool calls with:
  - Tool name and arguments
  - Result (full API response)
  - Success/failure status
  - Timestamp and elapsed time
- Outcome checks (which ground truth checks passed/failed)
- Reward breakdown (structural, ground_truth, efficiency, penalty, total)

## Reward Modes

Two modes are available via `--reward-mode`. See [reward-system.md](reward-system.md) for detailed formulas and comparison.

- **`custom`** (default) — Episode-level. Scores tool selection, efficiency, and ground truth after the episode ends.
- **`openenv`** — Per-step. Each tool call is scored by an OpenEnv Transform as it happens, then combined with ground truth.

## Supported Models

Any model supported by [LiteLLM](https://docs.litellm.ai/docs/providers):

| Provider | Example | Env Var |
|---|---|---|
| OpenAI | `gpt-4o`, `gpt-5.4`, `o3-pro` | `OPENAI_API_KEY` |
| Anthropic | `claude-opus-4-6`, `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| Ollama (local) | `ollama/llama3`, `ollama/mistral` | — (no key needed) |
| Google | `gemini/gemini-pro` | `GEMINI_API_KEY` |
| And 100+ more... | See LiteLLM docs | Varies |

## GYM_REGISTRY

`run_eval.py` uses a registry to map gym names to their configurations:

```python
GYM_REGISTRY = {
    "inventory": {
        "scenarios_loader": ...,     # what to test
        "checker_factory": ...,      # how to verify ground truth
        "transform_factory": ...,    # per-step reward transform
        "default_openenv_url": ...,  # where the gym is running
        "default_api_url": ...,      # where the backend API is
    },
}
```

To add a new gym, add an entry here. See [creating-a-new-gym.md](creating-a-new-gym.md) for the full process.
