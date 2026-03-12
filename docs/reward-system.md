# Reward System

Two reward modes are available, selectable via `--reward-mode` in `run_eval.py`. Both share the same ground truth verification and hallucination penalty — the difference is how per-step performance is scored.

## Custom Mode (`--reward-mode custom`)

Episode-level reward from `rewards/base.py`. Evaluates the agent **after the episode ends**, looking at the full picture.

| Component | Weight | What it checks | How it's calculated |
|---|---|---|---|
| **Structural** | 0.25 | Did the agent call the right tools without errors? | `0.6 × F1(expected, used) + 0.4 × success_rate` |
| **Ground Truth** | 0.60 | Does the database match the expected outcome? | `passed_checks / total_checks` |
| **Efficiency** | 0.15 | Did the agent solve it in a reasonable number of steps? | `min(expected_steps / actual_steps, 1.0)` |
| **Penalty** | -1.0 | Hallucination: tools say success but DB disagrees | Applied when ALL steps succeed AND zero ground truth checks pass |

**Total** = `0.25 × structural + 0.60 × ground_truth + 0.15 × efficiency + penalty`

Clamped to [-1.0, 1.0].

### What custom mode captures

- **Tool selection**: Did the agent pick the correct tools for the task? (F1 score against expected tools)
- **Execution quality**: Did the tools succeed or fail?
- **Step efficiency**: Did the agent solve it quickly or waste steps?
- **Correctness**: Did the final database state match expectations?

## OpenEnv Mode (`--reward-mode openenv`)

Per-step reward from `rewards/transforms/` combined with ground truth. Evaluates each tool call **as it happens** using OpenEnv's native Transform pipeline.

| Component | Weight | What it checks | How it's calculated |
|---|---|---|---|
| **Step Rewards** | 0.40 | Did each tool call produce a quality result? | Average per-step reward, normalized to [0, 1] |
| **Ground Truth** | 0.60 | Does the database match the expected outcome? | `passed_checks / total_checks` (same as custom) |
| **Penalty** | -1.0 | Hallucination: step rewards positive but DB disagrees | Same logic as custom |

**Total** = `0.40 × step_score + 0.60 × ground_truth + penalty`

Clamped to [-1.0, 1.0].

### How per-step rewards work

Each gym defines a **Transform** subclass that inspects the raw observation after each tool call and assigns a reward. The transform sees **one observation at a time** — it has no access to the scenario, expected tools, or step count.

Per-step reward values are gym-specific. For the Inventory gym (`rewards/transforms/inventory.py`):

| Result type | Reward | Example |
|---|---|---|
| Entity created/retrieved (dict with `id`) | **1.0** | `create_product` → `{"id": 1, ...}` |
| Listed entities (non-empty list) | **0.8** | `list_products` → `[{...}, {...}]` |
| Valid but empty/minimal result | **0.5** | `search_products` → `[]` |
| Error (API returned error) | **-0.5** | Invalid arguments, server error |
| Non-tool observation | **0.0** | System messages, resets |

The raw average of step rewards is **normalized** to [0, 1]:

```
step_score = (avg_step_reward + 0.5) / 1.5
```

This maps the reward range [-0.5, 1.0] to [0.0, 1.0].

### What OpenEnv mode captures

- **Result quality**: Does each tool call return a meaningful result? (graded, not just pass/fail)
- **Error detection**: Are there API errors or invalid arguments?
- **Correctness**: Same ground truth check as custom mode

### What OpenEnv mode does NOT capture

- **Tool selection**: The transform sees one observation — it doesn't know which tools *should* have been called
- **Efficiency**: No access to expected step count or scenario definition

## Comparison

| Check | Custom | OpenEnv |
|---|:---:|:---:|
| Tool selection (right tools?) | F1 score | — |
| Execution success | Boolean (pass/fail) | Graded (1.0/0.8/0.5/-0.5) |
| Result content quality | — | Inspects response structure |
| Step efficiency | `expected / actual` | — |
| Ground truth (DB check) | 0.60 weight | 0.60 weight |
| Hallucination penalty | -1.0 | -1.0 |

**Why two modes?** They measure different things. Custom asks *"did the agent follow the right plan?"* (tool selection + efficiency). OpenEnv asks *"did each step produce a quality result?"* (per-step result validation). Running both gives a fuller picture — see `results/inventory/comparison_custom_vs_openenv.md` for real results.

## Hallucination Penalty (both modes)

A **-1.0 penalty** is applied when all tool calls appear successful but the database shows nothing actually happened. This catches models that "hallucinate" — generating convincing-looking tool calls that don't actually achieve anything.

Trigger condition: all step rewards > 0 (or all steps succeed) **AND** zero ground truth checks pass.

## Adding Rewards for a New Gym

1. **Ground truth checker** (`rewards/<gym>_checks.py`): Queries the actual backend to verify expected outcomes
2. **Step transform** (`rewards/transforms/<gym>.py`): Subclass `StepRewardTransform`, override `_compute_reward()` with gym-specific scoring logic
3. **Register** both in `run_eval.py` → `GYM_REGISTRY`

The generic `StepRewardTransform` (in `rewards/transforms/base.py`) works as a fallback — it gives 1.0 for any successful tool call and -0.5 for errors. Create a gym-specific subclass for more nuanced scoring.

## Files

| File | Role |
|------|------|
| `rewards/base.py` | `RewardCalculator` (custom mode) + `RewardBreakdown` (shared) |
| `rewards/inventory_checks.py` | Inventory ground truth checker (queries SQLite via API) |
| `rewards/transforms/base.py` | `StepRewardTransform` (generic) + `OpenEnvRewardCalculator` |
| `rewards/transforms/inventory.py` | `InventoryStepTransform` (inventory-specific per-step scoring) |
