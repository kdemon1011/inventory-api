# Inventory Gym — Evaluation Results

Evaluation results for the **inventory** gym across **12 LLM models** (OpenAI + Anthropic).

All actions go through OpenEnv (`LLM → OpenEnv → Inventory API`). Rewards are computed by `rewards/base.py` using:
- **Structural** (0.25) — right tools called, no errors
- **Ground Truth** (0.60) — database state matches expected outcome
- **Efficiency** (0.15) — solved in reasonable steps
- **Hallucination Penalty** (-1.0) — tools say success but DB disagrees

---

## How to Reproduce

**Prerequisites** — start both servers before running any evaluation:

```bash
# 1. Reset DB + start Inventory API & OpenEnv server
cd inventory && rm -f data/app.db && python main.py
```

**Run a single model:**

```bash
python run_eval.py --gym inventory --model <model_name> --save --output results/inventory.md
```

> **Note**: GPT-5, GPT-5-mini, o3-mini, and o4-mini require `--temperature 1.0` (reasoning models don't support temperature=0).

**Commands used for this evaluation:**

```bash
# OpenAI models
python run_eval.py --gym inventory --model gpt-4o --save --output results/inventory.md
python run_eval.py --gym inventory --model gpt-3.5-turbo --save --output results/inventory.md
python run_eval.py --gym inventory --model gpt-4o-mini --save --output results/inventory.md
python run_eval.py --gym inventory --model gpt-4 --save --output results/inventory.md
python run_eval.py --gym inventory --model gpt-4-turbo --save --output results/inventory.md
python run_eval.py --gym inventory --model o3-mini --temperature 1.0 --save --output results/inventory.md
python run_eval.py --gym inventory --model gpt-5 --temperature 1.0 --save --output results/inventory.md
python run_eval.py --gym inventory --model gpt-5-mini --temperature 1.0 --save --output results/inventory.md
python run_eval.py --gym inventory --model o4-mini --temperature 1.0 --save --output results/inventory.md

# Anthropic models
python run_eval.py --gym inventory --model claude-opus-4-20250514 --save --output results/inventory.md
python run_eval.py --gym inventory --model claude-sonnet-4-20250514 --save --output results/inventory.md
python run_eval.py --gym inventory --model claude-3-haiku-20240307 --save --output results/inventory.md
```

> **Local models (Ollama):**
> ```bash
> ollama serve && ollama pull llama3
> python run_eval.py --gym inventory --model ollama/llama3 --save --output results/inventory.md
> ```

---

## Summary — Model Comparison

| Rank | Model | Provider | Avg Reward | Total Time | Notes |
|:---:|---|---|:---:|:---:|---|
| 🥇 | **gpt-4o** | OpenAI | **0.89** | 50.7s | Best overall — fast and accurate |
| 🥈 | **gpt-3.5-turbo** | OpenAI | **0.76** | 60.5s | Best value — cheap and strong |
| 🥉 | **gpt-5** | OpenAI | **0.72** | 401.6s | Accurate but slow (temp=1 required) |
| 4 | **claude-opus-4-20250514** | Anthropic | **0.72** | 241.0s | Strong accuracy, moderate speed |
| 5 | **gpt-5-mini** | OpenAI | **0.72** | 307.7s | Matches GPT-5, slightly faster |
| 6 | **claude-sonnet-4-20250514** | Anthropic | **0.71** | 193.4s | Good accuracy, Anthropic's best value |
| 7 | **o4-mini** | OpenAI | **0.71** | 218.2s | Latest reasoning model, temp=1 required |
| 8 | **gpt-4o-mini** | OpenAI | **0.69** | 92.1s | Decent but too many retry steps |
| 9 | **gpt-4** | OpenAI | **0.67** | 187.7s | Older model, still decent |
| 10 | **o3-mini** | OpenAI | **0.66** | 291.3s | Reasoning model, 1 scenario error |
| 11 | **gpt-4-turbo** | OpenAI | **0.63** | 162.3s | Retry loops hurt efficiency |
| 12 | **claude-3-haiku-20240307** | Anthropic | **0.52*** | 87.5s | Rate-limited (3/10 failed) |

\* *Claude Haiku hit Anthropic rate limits on the last 3 scenarios. Completed 7/10 scored 0.74 avg.*

---

### Per-Scenario Comparison (Total Reward)

| Scenario | gpt-4o | gpt-3.5 | gpt-5 | opus-4 | gpt-5-mini | sonnet-4 | o4-mini | gpt-4o-mini | gpt-4 | o3-mini | gpt-4-turbo | haiku |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 1.00 | 0.80 | 0.52 | 0.48 | 0.48 | 0.48 | 0.48 | 0.80 | 0.50 | 0.57 | 0.52 | 0.50 |
| create_and_verify | 1.00 | 0.81 | 0.83 | 0.84 | 0.84 | 0.89 | 0.84 | 0.76 | 0.81 | 0.82 | 0.61 | 0.83 |
| product_and_order | 0.80 | 0.62 | 0.58 | 0.61 | 0.65 | 0.63 | 0.69 | 0.62 | 0.60 | 0.62 | 0.55 | 0.62 |
| update_price | 1.00 | 0.95 | 0.88 | 0.83 | 0.82 | 0.83 | 0.84 | 0.76 | 0.80 | 0.82 | 0.81 | 0.75 |
| search_product | 1.00 | 0.88 | 0.89 | 0.84 | 0.89 | 0.89 | 0.89 | 0.76 | 0.80 | 0.95 | 0.95 | 0.85 |
| deactivate | 1.00 | 0.95 | 0.88 | 0.88 | 0.82 | 0.77 | 0.76 | 0.76 | 0.77 | 0.82 | 0.74 | 0.76 |
| bulk_creation | 0.95 | 0.81 | 0.88 | 0.88 | 0.88 | 0.88 | 0.85 | 0.73 | 0.75 | 0.82 | 0.74 | 0.84 |
| full_order | 0.70 | 0.56 | 0.56 | 0.56 | 0.55 | 0.56 | 0.53 | 0.54 | 0.51 | 0.52 | 0.43 | ERR |
| multi_item_order | 0.65 | 0.50 | 0.49 | 0.59 | 0.54 | 0.54 | 0.49 | 0.50 | 0.50 | ERR | 0.44 | ERR |
| price_then_order | 0.80 | 0.78 | 0.73 | 0.68 | 0.73 | 0.65 | 0.68 | 0.66 | 0.69 | 0.70 | 0.52 | ERR |
| **Average** | **0.89** | **0.76** | **0.72** | **0.72** | **0.72** | **0.71** | **0.71** | **0.69** | **0.67** | **0.66** | **0.63** | **0.52** |

---

### Key Observations

1. **gpt-4o dominates** — perfect scores on 6/10 scenarios, only drops on order-related tasks. Fastest overall.
2. **Order scenarios are hardest** — `full_order_workflow`, `multi_item_order`, and `product_and_order` consistently lowest across all 12 models (require chaining product IDs correctly).
3. **GPT-5 family = same accuracy as Claude Opus/Sonnet 4 but much slower** — all land at 0.71–0.72 avg. The temperature=1 constraint adds non-determinism.
4. **gpt-3.5-turbo is the best value** — 0.76 avg at a fraction of the cost and 60s total time.
5. **Claude Opus 4 ≈ Claude Sonnet 4** — nearly identical scores (0.72 vs 0.71), Opus is slower and more expensive.
6. **Efficiency matters** — models that retry or call unnecessary tools get penalized. gpt-4o averages 2.5 steps/scenario vs 5+ for most others.
7. **No hallucinations detected** — zero models triggered the -1.0 penalty across all evaluations.
8. **Reasoning models (o3-mini, o4-mini, gpt-5) don't help here** — tool-calling tasks don't benefit from chain-of-thought reasoning; they just add latency.

---

## Detailed Results per Model

---

### Model: `gpt-4o`

- **Date**: 2026-03-11 00:36:13
- **Temperature**: 0.0
- **Total Time**: 50.7s

```bash
python run_eval.py --gym inventory --model gpt-4o --save --output results/inventory.md
```

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 1 | 4.4s |
| create_and_verify_product | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 2 | 4.4s |
| product_and_order | 1.00 | 0.67 | 1.00 | 0.00 | **0.80** | 2 | 3.7s |
| update_product_price | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 2 | 4.4s |
| search_product | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 2 | 3.0s |
| deactivate_product | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 2 | 3.1s |
| bulk_product_creation | 1.00 | 1.00 | 0.67 | 0.00 | **0.95** | 3 | 3.6s |
| full_order_workflow | 1.00 | 0.50 | 1.00 | 0.00 | **0.70** | 3 | 8.7s |
| multi_item_order | 1.00 | 0.50 | 0.67 | 0.00 | **0.65** | 3 | 7.2s |
| price_change_then_order | 1.00 | 0.67 | 1.00 | 0.00 | **0.80** | 4 | 8.0s |

**Average Reward: 0.89**

---

### Model: `gpt-3.5-turbo`

- **Date**: 2026-03-11 00:40:23
- **Temperature**: 0.0
- **Total Time**: 60.5s

```bash
python run_eval.py --gym inventory --model gpt-3.5-turbo --save --output results/inventory.md
```

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 0.60 | 1.00 | 0.33 | 0.00 | **0.80** | 3 | 4.7s |
| create_and_verify_product | 0.43 | 1.00 | 0.67 | 0.00 | **0.81** | 3 | 4.1s |
| product_and_order | 0.67 | 0.67 | 0.33 | 0.00 | **0.62** | 6 | 7.9s |
| update_product_price | 0.80 | 1.00 | 1.00 | 0.00 | **0.95** | 2 | 4.9s |
| search_product | 0.73 | 1.00 | 0.67 | 0.00 | **0.88** | 3 | 6.3s |
| deactivate_product | 0.80 | 1.00 | 1.00 | 0.00 | **0.95** | 2 | 3.2s |
| bulk_product_creation | 0.66 | 1.00 | 0.29 | 0.00 | **0.81** | 7 | 8.3s |
| full_order_workflow | 0.58 | 0.50 | 0.75 | 0.00 | **0.56** | 4 | 5.4s |
| multi_item_order | 0.65 | 0.50 | 0.25 | 0.00 | **0.50** | 8 | 10.6s |
| price_change_then_order | 0.90 | 0.67 | 1.00 | 0.00 | **0.78** | 4 | 5.1s |

**Average Reward: 0.76**

---

### Model: `gpt-5`

- **Date**: 2026-03-11 01:25:00
- **Temperature**: 1.0 *(GPT-5 requires temperature=1)*
- **Total Time**: 401.6s

```bash
python run_eval.py --gym inventory --model gpt-5 --temperature 1.0 --save --output results/inventory.md
```

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 0.60 | 0.50 | 0.50 | 0.00 | **0.52** | 2 | 21.4s |
| create_and_verify_product | 0.68 | 1.00 | 0.67 | 0.00 | **0.83** | 3 | 27.5s |
| product_and_order | 0.59 | 0.67 | 0.25 | 0.00 | **0.58** | 8 | 40.1s |
| update_product_price | 0.73 | 1.00 | 1.00 | 0.00 | **0.88** | 2 | 21.2s |
| search_product | 0.75 | 1.00 | 0.67 | 0.00 | **0.89** | 3 | 30.4s |
| deactivate_product | 0.73 | 1.00 | 1.00 | 0.00 | **0.88** | 2 | 24.3s |
| bulk_product_creation | 0.73 | 1.00 | 0.67 | 0.00 | **0.88** | 3 | 28.3s |
| full_order_workflow | 0.73 | 0.50 | 0.50 | 0.00 | **0.56** | 6 | 64.6s |
| multi_item_order | 0.61 | 0.50 | 0.25 | 0.00 | **0.49** | 8 | 77.2s |
| price_change_then_order | 0.78 | 0.67 | 0.67 | 0.00 | **0.73** | 5 | 66.4s |

**Average Reward: 0.72**

---

### Model: `claude-opus-4-20250514`

- **Date**: 2026-03-11 01:20:00
- **Temperature**: 0.0
- **Total Time**: 241.0s

```bash
python run_eval.py --gym inventory --model claude-opus-4-20250514 --save --output results/inventory.md
```

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 0.53 | 0.50 | 0.33 | 0.00 | **0.48** | 3 | 16.0s |
| create_and_verify_product | 0.68 | 1.00 | 0.50 | 0.00 | **0.84** | 4 | 21.7s |
| product_and_order | 0.64 | 0.67 | 0.33 | 0.00 | **0.61** | 6 | 25.8s |
| update_product_price | 0.51 | 1.00 | 0.67 | 0.00 | **0.83** | 3 | 20.5s |
| search_product | 0.56 | 1.00 | 0.50 | 0.00 | **0.84** | 4 | 23.2s |
| deactivate_product | 0.73 | 1.00 | 1.00 | 0.00 | **0.88** | 2 | 11.9s |
| bulk_product_creation | 0.73 | 1.00 | 0.67 | 0.00 | **0.88** | 3 | 19.2s |
| full_order_workflow | 0.73 | 0.50 | 0.50 | 0.00 | **0.56** | 6 | 33.8s |
| multi_item_order | 0.75 | 0.50 | 0.67 | 0.00 | **0.59** | 3 | 20.2s |
| price_change_then_order | 0.73 | 0.67 | 0.44 | 0.00 | **0.68** | 9 | 48.4s |

**Average Reward: 0.72**

---

### Model: `gpt-5-mini`

- **Date**: 2026-03-11 01:35:00
- **Temperature**: 1.0 *(GPT-5-mini requires temperature=1)*
- **Total Time**: 307.7s

```bash
python run_eval.py --gym inventory --model gpt-5-mini --temperature 1.0 --save --output results/inventory.md
```

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 0.53 | 0.50 | 0.33 | 0.00 | **0.48** | 3 | 14.2s |
| create_and_verify_product | 0.68 | 1.00 | 0.50 | 0.00 | **0.84** | 4 | 22.4s |
| product_and_order | 0.66 | 0.67 | 0.50 | 0.00 | **0.65** | 4 | 28.7s |
| update_product_price | 0.40 | 1.00 | 0.40 | 0.00 | **0.82** | 5 | 26.0s |
| search_product | 0.75 | 1.00 | 0.67 | 0.00 | **0.89** | 3 | 27.7s |
| deactivate_product | 0.46 | 1.00 | 0.40 | 0.00 | **0.82** | 5 | 26.5s |
| bulk_product_creation | 0.73 | 1.00 | 0.67 | 0.00 | **0.88** | 3 | 20.5s |
| full_order_workflow | 0.73 | 0.50 | 0.50 | 0.00 | **0.55** | 6 | 54.3s |
| multi_item_order | 0.68 | 0.50 | 0.50 | 0.00 | **0.54** | 4 | 37.9s |
| price_change_then_order | 0.78 | 0.67 | 0.67 | 0.00 | **0.73** | 5 | 49.5s |

**Average Reward: 0.72**

---

### Model: `claude-sonnet-4-20250514`

- **Date**: 2026-03-11 01:12:10
- **Temperature**: 0.0
- **Total Time**: 193.4s

```bash
python run_eval.py --gym inventory --model claude-sonnet-4-20250514 --save --output results/inventory.md
```

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 0.53 | 0.50 | 0.33 | 0.00 | **0.48** | 3 | 18.2s |
| create_and_verify_product | 0.75 | 1.00 | 0.67 | 0.00 | **0.89** | 3 | 13.9s |
| product_and_order | 0.66 | 0.67 | 0.40 | 0.00 | **0.63** | 5 | 22.5s |
| update_product_price | 0.51 | 1.00 | 0.67 | 0.00 | **0.83** | 3 | 17.9s |
| search_product | 0.75 | 1.00 | 0.67 | 0.00 | **0.89** | 3 | 14.6s |
| deactivate_product | 0.46 | 1.00 | 0.40 | 0.00 | **0.77** | 5 | 15.9s |
| bulk_product_creation | 0.73 | 1.00 | 0.67 | 0.00 | **0.88** | 3 | 15.0s |
| full_order_workflow | 0.73 | 0.50 | 0.50 | 0.00 | **0.56** | 6 | 27.0s |
| multi_item_order | 0.68 | 0.50 | 0.50 | 0.00 | **0.54** | 4 | 18.2s |
| price_change_then_order | 0.65 | 0.67 | 0.57 | 0.00 | **0.65** | 7 | 30.0s |

**Average Reward: 0.71**

---

### Model: `o4-mini`

- **Date**: 2026-03-11 01:42:00
- **Temperature**: 1.0 *(O-series requires temperature=1)*
- **Total Time**: 218.2s

```bash
python run_eval.py --gym inventory --model o4-mini --temperature 1.0 --save --output results/inventory.md
```

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 0.53 | 0.50 | 0.33 | 0.00 | **0.48** | 3 | 8.1s |
| create_and_verify_product | 0.68 | 1.00 | 0.50 | 0.00 | **0.84** | 4 | 15.2s |
| product_and_order | 0.80 | 0.67 | 0.67 | 0.00 | **0.69** | 3 | 18.2s |
| update_product_price | 0.56 | 1.00 | 0.50 | 0.00 | **0.84** | 4 | 15.6s |
| search_product | 0.75 | 1.00 | 0.67 | 0.00 | **0.89** | 3 | 12.8s |
| deactivate_product | 0.40 | 1.00 | 0.40 | 0.00 | **0.76** | 5 | 18.7s |
| bulk_product_creation | 0.60 | 1.00 | 0.50 | 0.00 | **0.85** | 4 | 16.8s |
| full_order_workflow | 0.65 | 0.50 | 0.25 | 0.00 | **0.53** | 8 | 41.7s |
| multi_item_order | 0.61 | 0.50 | 0.25 | 0.00 | **0.49** | 8 | 21.4s |
| price_change_then_order | 0.73 | 0.67 | 0.57 | 0.00 | **0.68** | 7 | 49.5s |

**Average Reward: 0.71**

---

### Model: `gpt-4o-mini`

- **Date**: 2026-03-11 00:38:43
- **Temperature**: 0.0
- **Total Time**: 92.1s

```bash
python run_eval.py --gym inventory --model gpt-4o-mini --save --output results/inventory.md
```

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 0.60 | 1.00 | 0.33 | 0.00 | **0.80** | 3 | 5.2s |
| create_and_verify_product | 0.40 | 1.00 | 0.40 | 0.00 | **0.76** | 5 | 8.8s |
| product_and_order | 0.64 | 0.67 | 0.40 | 0.00 | **0.62** | 5 | 8.4s |
| update_product_price | 0.40 | 1.00 | 0.40 | 0.00 | **0.76** | 5 | 7.3s |
| search_product | 0.40 | 1.00 | 0.40 | 0.00 | **0.76** | 5 | 7.9s |
| deactivate_product | 0.40 | 1.00 | 0.40 | 0.00 | **0.76** | 5 | 6.3s |
| bulk_product_creation | 0.40 | 1.00 | 0.20 | 0.00 | **0.73** | 10 | 13.7s |
| full_order_workflow | 0.69 | 0.50 | 0.43 | 0.00 | **0.54** | 7 | 12.8s |
| multi_item_order | 0.61 | 0.50 | 0.33 | 0.00 | **0.50** | 6 | 10.4s |
| price_change_then_order | 0.65 | 0.67 | 0.67 | 0.00 | **0.66** | 6 | 11.0s |

**Average Reward: 0.69**

---

### Model: `gpt-4`

- **Date**: 2026-03-11 00:55:16
- **Temperature**: 0.0
- **Total Time**: 187.7s

```bash
python run_eval.py --gym inventory --model gpt-4 --save --output results/inventory.md
```

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 0.60 | 0.50 | 0.33 | 0.00 | **0.50** | 3 | 10.3s |
| create_and_verify_product | 0.43 | 1.00 | 0.67 | 0.00 | **0.81** | 3 | 12.6s |
| product_and_order | 0.40 | 0.67 | 0.67 | 0.00 | **0.60** | 3 | 15.4s |
| update_product_price | 0.40 | 1.00 | 0.67 | 0.00 | **0.80** | 3 | 13.1s |
| search_product | 0.40 | 1.00 | 0.67 | 0.00 | **0.80** | 3 | 17.4s |
| deactivate_product | 0.40 | 1.00 | 0.50 | 0.00 | **0.77** | 4 | 19.9s |
| bulk_product_creation | 0.40 | 1.00 | 0.33 | 0.00 | **0.75** | 6 | 26.8s |
| full_order_workflow | 0.57 | 0.50 | 0.43 | 0.00 | **0.51** | 7 | 28.1s |
| multi_item_order | 0.40 | 0.50 | 0.67 | 0.00 | **0.50** | 3 | 12.9s |
| price_change_then_order | 0.83 | 0.67 | 0.57 | 0.00 | **0.69** | 7 | 31.1s |

**Average Reward: 0.67**

---

### Model: `o3-mini`

- **Date**: 2026-03-11 00:51:25
- **Temperature**: 1.0 *(O-series requires temperature=1)*
- **Total Time**: 291.3s

```bash
python run_eval.py --gym inventory --model o3-mini --temperature 1.0 --save --output results/inventory.md
```

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 0.80 | 0.50 | 0.50 | 0.00 | **0.57** | 2 | 15.3s |
| create_and_verify_product | 0.64 | 1.00 | 0.40 | 0.00 | **0.82** | 5 | 20.6s |
| product_and_order | 0.64 | 0.67 | 0.40 | 0.00 | **0.62** | 5 | 32.1s |
| update_product_price | 0.64 | 1.00 | 0.40 | 0.00 | **0.82** | 5 | 24.2s |
| search_product | 0.80 | 1.00 | 1.00 | 0.00 | **0.95** | 2 | 15.2s |
| deactivate_product | 0.64 | 1.00 | 0.40 | 0.00 | **0.82** | 5 | 29.1s |
| bulk_product_creation | 0.67 | 1.00 | 0.33 | 0.00 | **0.82** | 6 | 35.1s |
| full_order_workflow | 0.65 | 0.50 | 0.38 | 0.00 | **0.52** | 8 | 33.1s |
| multi_item_order | — | — | — | — | **ERROR** | 0 | 23.6s |
| price_change_then_order | 0.80 | 0.67 | 0.67 | 0.00 | **0.70** | 6 | 62.8s |

**Average Reward: 0.66**

---

### Model: `gpt-4-turbo`

- **Date**: 2026-03-11 00:45:01
- **Temperature**: 0.0
- **Total Time**: 162.3s

```bash
python run_eval.py --gym inventory --model gpt-4-turbo --save --output results/inventory.md
```

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 0.60 | 0.50 | 0.50 | 0.00 | **0.52** | 2 | 14.4s |
| create_and_verify_product | 0.40 | 0.75 | 0.40 | 0.00 | **0.61** | 5 | 11.9s |
| product_and_order | 0.40 | 0.67 | 0.33 | 0.00 | **0.55** | 6 | 14.3s |
| update_product_price | 0.43 | 1.00 | 0.67 | 0.00 | **0.81** | 3 | 14.2s |
| search_product | 0.80 | 1.00 | 1.00 | 0.00 | **0.95** | 2 | 11.4s |
| deactivate_product | 0.37 | 1.00 | 0.33 | 0.00 | **0.74** | 6 | 11.3s |
| bulk_product_creation | 0.40 | 1.00 | 0.25 | 0.00 | **0.74** | 8 | 18.8s |
| full_order_workflow | 0.30 | 0.50 | 0.38 | 0.00 | **0.43** | 8 | 19.8s |
| multi_item_order | 0.40 | 0.50 | 0.25 | 0.00 | **0.44** | 8 | 24.1s |
| price_change_then_order | 0.24 | 0.67 | 0.40 | 0.00 | **0.52** | 10 | 22.0s |

**Average Reward: 0.63**

---

### Model: `claude-3-haiku-20240307`

- **Date**: 2026-03-11 01:15:43
- **Temperature**: 0.0
- **Total Time**: 87.5s
- **⚠️ Note**: Hit Anthropic rate limit after scenario 7/10. Last 3 scenarios failed.

```bash
python run_eval.py --gym inventory --model claude-3-haiku-20240307 --save --output results/inventory.md
```

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| create_product | 0.60 | 0.50 | 0.33 | 0.00 | **0.50** | 3 | 7.3s |
| create_and_verify_product | 0.68 | 1.00 | 0.40 | 0.00 | **0.83** | 5 | 12.0s |
| product_and_order | 0.64 | 0.67 | 0.40 | 0.00 | **0.62** | 5 | 13.8s |
| update_product_price | 0.38 | 1.00 | 0.40 | 0.00 | **0.75** | 5 | 11.6s |
| search_product | 0.70 | 1.00 | 0.50 | 0.00 | **0.85** | 4 | 10.8s |
| deactivate_product | 0.40 | 1.00 | 0.40 | 0.00 | **0.76** | 5 | 12.0s |
| bulk_product_creation | 0.72 | 1.00 | 0.40 | 0.00 | **0.84** | 5 | 12.6s |
| full_order_workflow | — | — | — | — | **ERROR** | 0 | 6.5s |
| multi_item_order | — | — | — | — | **ERROR** | 0 | 0.4s |
| price_change_then_order | — | — | — | — | **ERROR** | 0 | 0.4s |

**Average Reward: 0.52** *(0.74 for completed scenarios)*

---

## Running with Local Models (Ollama)

Ollama was not available in this environment (requires `sudo` for installation). To run local models:

```bash
# 1. Install Ollama (requires sudo)
curl -fsSL https://ollama.com/install.sh | sh

# 2. Start Ollama server
ollama serve &

# 3. Pull models
ollama pull llama3          # Meta Llama 3 8B
ollama pull mistral         # Mistral 7B
ollama pull qwen2           # Qwen2 7B

# 4. Run evaluation
python run_eval.py --gym inventory --model ollama/llama3 --save --output results/inventory.md
python run_eval.py --gym inventory --model ollama/mistral --save --output results/inventory.md
python run_eval.py --gym inventory --model ollama/qwen2 --save --output results/inventory.md
```

> **Tip**: Local models may require higher `--max-tokens` (e.g. 2048) and may need `--temperature 0.1` for better tool-calling behavior.
