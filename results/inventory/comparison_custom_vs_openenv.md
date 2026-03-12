# Custom Rewards vs OpenEnv Transform Rewards — Comparison

**Custom Run**: `run_20260311_1830` — 16 models, episode-level reward calculation
**OpenEnv Run**: `run_20260312_0100` — 9 models, per-step transform reward calculation

This document compares the **9 models** evaluated under both reward systems to understand how each system scores model behavior differently and why scores diverge.

---

## How Each Reward System Works

### Custom Rewards (`rewards/base.py`)

| Component | Weight | What It Measures |
|---|:---:|---|
| **Structural** | 0.25 | Were the right tools called without API errors? (binary per-scenario) |
| **Ground Truth** | 0.60 | Does the final database state match expected outcome? |
| **Efficiency** | 0.15 | Was it solved in ≤ optimal steps? (ratio: optimal/actual) |
| **Hallucination Penalty** | -1.0 | Tools reported success but DB disagrees |

> Custom rewards are **lenient on tool execution quality** — if the tools were called and the DB is correct, you get a high score regardless of extra calls, retries, or messy intermediate results.

### OpenEnv Transform Rewards (`rewards/transforms/`)

| Component | Weight | What It Measures |
|---|:---:|---|
| **Step Rewards** | 0.40 | Per-step quality: each tool call is scored individually based on response structure |
| **Ground Truth** | 0.60 | Same as custom — final DB state verification |
| **Hallucination Penalty** | -1.0 | Same as custom |

Per-step scoring logic (`InventoryStepTransform`):
- **Error response** → `-0.5` (API returned an error)
- **Created/retrieved entity** (dict with `id`) → `+1.0`
- **Listed entities** (non-empty list) → `+0.8`
- **Valid but minimal/unclear result** → `+0.5`
- **Non-tool observation** → `0.0`

> OpenEnv rewards are **strict on every tool call** — extra steps, failed attempts, and unclear responses all drag the score down. A model that retries or makes exploratory calls gets penalized even if the final result is correct.

---

## Side-by-Side Results

| # | Model | Custom | OpenEnv | Delta | Direction |
|:---:|---|:---:|:---:|:---:|:---:|
| 1 | `claude-opus-4-20250514` | 0.88 | **0.89** | +0.01 | ✅ Stable |
| 2 | `gpt-5` | 0.85 | **0.81** | -0.04 | ✅ Stable |
| 3 | `claude-sonnet-4-20250514` | 0.88 | 0.71 | -0.17 | ⚠️ Moderate drop |
| 4 | `gpt-5.4` | 0.89 | 0.70 | -0.19 | ⚠️ Moderate drop |
| 5 | `claude-sonnet-4-6` | 0.89 | 0.70 | -0.19 | ⚠️ Moderate drop |
| 6 | `claude-opus-4-6` | 0.89 | 0.68 | -0.21 | 🔻 Significant drop |
| 7 | `o3-pro` | 0.89 | 0.58 | -0.31 | 🔻 Significant drop |
| 8 | `gpt-5-mini` | 0.89 | 0.50 | -0.39 | 🔻 Large drop |
| 9 | `claude-3-haiku-20240307` | 0.68 | 0.25 | -0.43 | ❌ Collapsed |

**Custom Average (9 models): 0.87** | **OpenEnv Average (9 models): 0.65**

---

## Per-Scenario Comparison (All 9 Models)

### Simple Scenarios (1-2 optimal steps)

| Scenario | Custom Avg | OpenEnv Avg | Delta | Notes |
|---|:---:|:---:|:---:|---|
| `create_product` | 0.97 | 0.75 | -0.22 | OpenEnv penalizes extra verification calls |
| `create_and_verify_product` | 0.97 | 0.83 | -0.14 | Verification is expected here, closer scores |
| `update_product_price` | 1.00 | 0.82 | -0.18 | Extra reads before update hurt OpenEnv score |
| `search_product` | 1.00 | 0.77 | -0.23 | Models often add unnecessary pre-steps |
| `deactivate_product` | 1.00 | 0.73 | -0.27 | Similar pattern — exploratory calls penalized |

### Complex Scenarios (3-4+ optimal steps)

| Scenario | Custom Avg | OpenEnv Avg | Delta | Notes |
|---|:---:|:---:|:---:|---|
| `product_and_order` | 0.78 | 0.62 | -0.16 | Multi-entity creation, errors compound |
| `bulk_product_creation` | 0.93 | 0.77 | -0.16 | Extra items or retries lower step score |
| `full_order_workflow` | 0.67 | 0.50 | -0.17 | Most complex scenario, errors accumulate |
| `multi_item_order` | 0.63 | 0.50 | -0.13 | Complex but relatively consistent |
| `price_change_then_order` | 0.79 | 0.64 | -0.15 | Multi-stage, moderate divergence |

**Key pattern**: Simple scenarios show _larger_ divergence than complex ones. This is because custom rewards already penalize complex scenarios via lower ground truth scores, while OpenEnv penalizes both simple and complex scenarios for step-level inefficiency.

---

## Per-Model Deep Dive

### 1. `claude-opus-4-20250514` — ✅ The Gold Standard

| | Custom | OpenEnv |
|---|:---:|:---:|
| **Average** | 0.88 | **0.89** |
| **Steps (avg)** | 2.6 | 2.5 |

**Why it maintained its score**: Opus is the only model that _improved_ under OpenEnv. It uses minimal steps, almost every tool call returns a clean entity with an `id`, and it rarely makes exploratory or redundant calls. Its step rewards averaged 0.93–1.00 across most scenarios.

**Bottom line**: Opus demonstrates the ideal pattern — call exactly the right tools, in the right order, with correct parameters. Both reward systems agree this is excellent behavior.

---

### 2. `gpt-5` — ✅ Resilient Performer

| | Custom | OpenEnv |
|---|:---:|:---:|
| **Average** | 0.85 | **0.81** |
| **Steps (avg)** | 3.3 | 2.9 |

**Why it stayed close**: GPT-5 had a slightly lower custom score (0.85) because it occasionally used extra steps in complex scenarios (`product_and_order`: 6 steps, `full_order_workflow`: 5 steps). Under OpenEnv, most of its tool calls were clean (step rewards 0.87 for most scenarios), so the 40% step weight didn't hurt much. The -0.04 delta comes primarily from one bad scenario (`create_product`: step reward 0.00 due to response format issues).

**Bottom line**: GPT-5 is a reliable tool-caller that mostly gets clean responses. Its slightly lower custom score was due to step count, which OpenEnv handles differently — it cares about step _quality_ not just _quantity_.

---

### 3. `claude-sonnet-4-20250514` — ⚠️ Verbose but Correct

| | Custom | OpenEnv |
|---|:---:|:---:|
| **Average** | 0.88 | **0.71** |
| **Steps (avg)** | 2.5 | 4.2 |

**Why it dropped**: Sonnet used significantly more steps under OpenEnv (4.2 vs 2.5 avg). It tends to make "verification" calls — creating an entity, then immediately fetching it to confirm. Under custom rewards, these extra calls cost nothing (structural still 1.0, efficiency still reasonable). Under OpenEnv, each extra call that returns a list or ambiguous response scores 0.5–0.8 instead of 1.0, dragging down the step average.

Specific examples:
- `create_product`: 1 step (custom) → 3 steps (OpenEnv), step reward dropped to 0.29
- `deactivate_product`: 2 steps (custom) → 5 steps (OpenEnv), step reward 0.37
- `bulk_product_creation`: 3 steps (custom) → 3 steps (OpenEnv), step reward 0.29

**Bottom line**: Sonnet's "verify after every action" habit is harmless under custom rewards but costly under OpenEnv. The extra calls don't add errors, but they dilute the average step quality.

---

### 4. `gpt-5.4` — ⚠️ Fast but Imprecise

| | Custom | OpenEnv |
|---|:---:|:---:|
| **Average** | 0.89 | **0.70** |
| **Steps (avg)** | 2.4 | 3.4 |

**Why it dropped**: GPT-5.4 was the fastest model in custom mode (47.4s) with near-perfect scores. Under OpenEnv, it used more steps and many responses landed in the 0.5 range (valid but minimal structure). The step rewards of 0.22–0.43 for several scenarios indicate that while the API calls succeeded, the responses weren't always structured as expected (e.g., missing `id` fields in intermediate responses).

**Bottom line**: GPT-5.4 optimizes for speed and correctness but doesn't produce the cleanest intermediate results. Custom rewards don't care; OpenEnv does.

---

### 5. `claude-sonnet-4-6` — ⚠️ Extra Caution Hurts

| | Custom | OpenEnv |
|---|:---:|:---:|
| **Average** | 0.89 | **0.70** |
| **Steps (avg)** | 2.4 | 4.3 |

**Why it dropped**: Nearly identical pattern to Sonnet v1. The newer Sonnet (4-6) added even more steps on average (4.3 vs 4.2), with `multi_item_order` ballooning to 9 steps. Each additional step that isn't a clean entity creation/retrieval hurts the step reward average. Custom rewards still saw this as efficient (≤ optimal threshold), but OpenEnv scored each step individually.

**Bottom line**: Sonnet 4-6 inherits the "verify everything" tendency and adds more exploratory calls. Both Sonnets lose ~0.19 points under OpenEnv.

---

### 6. `claude-opus-4-6` — 🔻 Surprising Regression

| | Custom | OpenEnv |
|---|:---:|:---:|
| **Average** | 0.89 | **0.68** |
| **Steps (avg)** | 2.4 | 5.0 |

**Why it dropped more than expected**: The newer Opus (4-6) used **double the steps** compared to the original Opus (5.0 vs 2.5 avg). Despite being a more capable model overall, it adopted a more "thorough" approach — reading state before and after each mutation. Under custom rewards, this thoroughness was invisible (structural 1.0, efficiency 0.67+). Under OpenEnv, each extra read/verify call scored only 0.5 (no `id` in list responses), pulling the step average down to 0.13–0.47 range.

**Contrast with Opus 2025**: The older Opus was more direct and minimalist, which is exactly what OpenEnv rewards favor.

**Bottom line**: Being "newer" doesn't mean "better" under all reward schemes. Opus 4-6's thoroughness is penalized by OpenEnv's per-step scoring.

---

### 7. `o3-pro` — 🔻 Overthinking Champion

| | Custom | OpenEnv |
|---|:---:|:---:|
| **Average** | 0.89 | **0.58** |
| **Steps (avg)** | 2.6 | 4.9 |
| **Time** | 647.1s | **1515.0s** |

**Why it collapsed**: o3-pro is a "reasoning" model that thinks deeply before acting. Under custom rewards, this produced perfect structural scores and efficient step counts. Under OpenEnv, o3-pro used nearly double the steps AND each step took 2-3x longer. The extra steps were often "validation reads" that returned lists (score: 0.8) or ambiguous results (score: 0.5). Combined with one ERROR on `full_order_workflow`, the step rewards averaged 0.13–0.47.

Additionally, o3-pro's extreme latency (1515s vs 647s) suggests it was doing extensive internal reasoning per step, but the _quality_ of each tool call output wasn't proportionally better.

**Bottom line**: o3-pro's "think more, verify more" strategy is rewarded by custom scoring but heavily penalized by OpenEnv. It's the most dramatic example of the two systems disagreeing.

---

### 8. `gpt-5-mini` — 🔻 Structural Weakness Exposed

| | Custom | OpenEnv |
|---|:---:|:---:|
| **Average** | 0.89 | **0.50** |
| **Steps (avg)** | 2.4 | 5.0 |

**Why it plummeted**: GPT-5-mini achieved a near-perfect custom score (0.89) but dropped to 0.50 under OpenEnv — the largest drop among non-erroring models (Δ-0.39). The step rewards are **0.00 across ALL scenarios**, meaning every tool call was scored as either an error (-0.5) or non-tool (0.0) by the transform.

This reveals a critical insight: **GPT-5-mini's tool call responses have a different structure** than what `InventoryStepTransform` expects. The API calls succeed (DB state is correct, hence ground truth 0.50–1.00), but the response format doesn't match the `dict with id` or `non-empty list` patterns the transform checks for. Under custom rewards, only the DB state matters; under OpenEnv, the response structure matters too.

**Bottom line**: GPT-5-mini is functionally correct but structurally non-compliant. Custom rewards can't see this difference; OpenEnv exposes it immediately.

---

### 9. `claude-3-haiku-20240307` — ❌ Rate-Limited Collapse

| | Custom | OpenEnv |
|---|:---:|:---:|
| **Average** | 0.68 | **0.25** |
| **Completed Scenarios** | 10 (3 errors) | 4 (6 errors) |

**Why it collapsed**: Haiku was already the weakest model in custom mode (0.68), failing 3 complex scenarios outright. Under OpenEnv, it hit rate limits after only 4 scenarios, with 6 scenarios returning ERROR. The 4 completed scenarios scored poorly (step rewards 0.00–0.40) because Haiku's responses lack the structured entity format. Even `create_product` (simplest scenario) got a step reward of 0.00.

**Note**: This comparison is unfair due to the rate limit issue. A rerun would provide a more accurate OpenEnv score, though it would likely still be significantly lower than custom given the step reward pattern in the 4 completed scenarios.

**Bottom line**: Haiku's small context window and simpler architecture produce responses that neither reward system rates highly, but OpenEnv is especially harsh on its unstructured outputs.

---

## Key Findings

### 1. Custom Rewards Create a "Ceiling Effect"

7 of 9 models scored 0.88–0.89 under custom rewards, making it nearly impossible to differentiate top performers. OpenEnv rewards spread the range from 0.25 to 0.89, providing **much better model discrimination**.

| Metric | Custom | OpenEnv |
|---|:---:|:---:|
| Score Range | 0.68 – 0.89 | 0.25 – 0.89 |
| Std Deviation | 0.06 | 0.18 |
| Models above 0.85 | 8/9 | 2/9 |

### 2. Step Quality ≠ Final Correctness

The biggest revelation is that **models can produce correct final results through messy intermediate steps**. GPT-5-mini scores 0.89 custom (DB is correct) but 0.50 OpenEnv (tool calls have poor structure). This matters for:
- **Debugging**: Messy intermediates make it harder to diagnose failures
- **Reliability**: Models that "stumble into" correct answers may fail on harder tasks
- **Cost**: Extra steps = more API tokens = higher cost

### 3. "Verify After Action" Is Expensive Under OpenEnv

Models that read state before/after mutations (Sonnet, Opus 4-6, o3-pro) lose 0.17–0.31 points. This verification pattern is:
- **Good practice** in real-world software (validate your writes)
- **Penalized** by OpenEnv (each verification is a step with lower reward)

This is a legitimate design tension — OpenEnv rewards _efficiency_, while real-world robustness rewards _verification_.

### 4. Response Structure Matters

OpenEnv's `InventoryStepTransform` checks response format (dict with `id` vs list vs minimal). Models that return clean, structured responses (Opus 2025) score well. Models whose responses don't match expected patterns (GPT-5-mini) score poorly even when functionally correct.

### 5. Model Ranking Changes Significantly

| Rank | Custom | OpenEnv |
|:---:|---|---|
| 1 | gpt-5.4 / claude-opus-4-6 / sonnet-4-6 / etc. (0.89 tie) | **claude-opus-4-20250514** (0.89) |
| 2 | o3-pro / sonnet / opus (0.88 tie) | **gpt-5** (0.81) |
| 3 | gpt-5 (0.85) | claude-sonnet-4-20250514 (0.71) |
| 4 | claude-3-haiku (0.68) | gpt-5.4 / claude-sonnet-4-6 (0.70) |
| 5 | — | claude-opus-4-6 (0.68) |
| 6 | — | o3-pro (0.58) |
| 7 | — | gpt-5-mini (0.50) |
| 8 | — | claude-3-haiku (0.25) |

Under custom rewards, most models look equally good. Under OpenEnv, **claude-opus-4-20250514** and **gpt-5** clearly separate from the pack.

---

## Recommendation

Use **both reward systems together** for the most complete picture:

- **Custom rewards** tell you: _"Did the model accomplish the task?"_ (outcome-focused)
- **OpenEnv rewards** tell you: _"Did the model accomplish the task cleanly?"_ (process-focused)

A model scoring high on both (like `claude-opus-4-20250514`) is genuinely excellent. A model scoring high on custom but low on OpenEnv (like `gpt-5-mini`) works but may be fragile. A model scoring low on both (like `claude-3-haiku`) needs improvement.

---

_Generated: 2026-03-12 | Gym: inventory | Scenarios: 10_
