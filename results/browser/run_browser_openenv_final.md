# Browser Gym — Evaluation Results

**Run ID**: `run_browser_openenv_final`  
**Gym Version**: `0.1.0`

Evaluation results for the **browser** gym across different LLM models.

**Reward Mode**: `openenv` — per-step rewards from `rewards/transforms/` + ground truth

Each model is evaluated on the same set of scenarios. Rewards are computed using OpenEnv transforms:
- **Step Rewards** (0.40) — per-step success/failure from transform
- **Ground Truth** (0.60) — database state matches expected outcome
- **Hallucination Penalty** (-1.0) — tools say success but DB disagrees

Trajectories: `trajectories/browser/run_browser_openenv_final/`

---

## Model: `gpt-5.4`

- **Date**: 2026-03-14 23:32:55
- **Temperature**: 0.0
- **Reward Mode**: openenv
- **Total Time**: 185.3s
- **Trajectory**: `trajectories/browser/run_browser_openenv_final/gpt-5.4.json`

| Scenario | Step Rewards | Ground Truth | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| coupon_threshold_trap | 0.67 | 1.00 | 0.00 | **0.87** | 18 | 19.9s |
| stock_deplete_cancel_reorder | 0.75 | 1.00 | 0.00 | **0.90** | 14 | 14.4s |
| false_price_optimal_coupon | 0.74 | 1.00 | 0.00 | **0.90** | 10 | 10.5s |
| cross_user_cart_isolation | 0.67 | 1.00 | 0.00 | **0.87** | 23 | 22.4s |
| wishlist_move_vs_direct_add | 0.71 | 1.00 | 0.00 | **0.88** | 22 | 17.7s |
| out_of_stock_boundary | 0.58 | 1.00 | 0.00 | **0.83** | 13 | 14.3s |
| expired_coupon_cascade | 0.64 | 1.00 | 0.00 | **0.86** | 15 | 11.6s |
| review_cross_page_verify | 0.72 | 1.00 | 0.00 | **0.89** | 19 | 19.6s |
| profile_update_checkout_verify | 0.72 | 1.00 | 0.00 | **0.89** | 12 | 15.0s |
| contact_then_register_same_email | 0.65 | 1.00 | 0.00 | **0.86** | 16 | 14.6s |
| bulk_cart_ops_total_tracking | 0.78 | 1.00 | 0.00 | **0.91** | 16 | 13.5s |
| cheapest_expensive_cross_category | 0.69 | 1.00 | 0.00 | **0.88** | 14 | 11.3s |

**Average Reward: 0.88**

---

## Model: `claude-sonnet-4-6`

- **Date**: 2026-03-14 23:38:04
- **Temperature**: 0.0
- **Reward Mode**: openenv
- **Total Time**: 495.0s
- **Trajectory**: `trajectories/browser/run_browser_openenv_final/claude-sonnet-4-6.json`

| Scenario | Step Rewards | Ground Truth | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| coupon_threshold_trap | 0.67 | 1.00 | 0.00 | **0.87** | 18 | 49.1s |
| stock_deplete_cancel_reorder | 0.75 | 1.00 | 0.00 | **0.90** | 14 | 35.6s |
| false_price_optimal_coupon | 0.74 | 1.00 | 0.00 | **0.90** | 10 | 28.3s |
| cross_user_cart_isolation | 0.67 | 1.00 | 0.00 | **0.87** | 23 | 50.1s |
| wishlist_move_vs_direct_add | 0.72 | 1.00 | 0.00 | **0.89** | 22 | 53.9s |
| out_of_stock_boundary | 0.52 | 1.00 | 0.00 | **0.81** | 13 | 38.8s |
| expired_coupon_cascade | 0.63 | 1.00 | 0.00 | **0.85** | 13 | 36.7s |
| review_cross_page_verify | 0.72 | 1.00 | 0.00 | **0.89** | 19 | 42.4s |
| profile_update_checkout_verify | 0.73 | 1.00 | 0.00 | **0.89** | 13 | 39.9s |
| contact_then_register_same_email | 0.63 | 1.00 | 0.00 | **0.85** | 18 | 51.3s |
| bulk_cart_ops_total_tracking | 0.78 | 1.00 | 0.00 | **0.91** | 16 | 35.0s |
| cheapest_expensive_cross_category | 0.69 | 1.00 | 0.00 | **0.88** | 14 | 33.3s |

**Average Reward: 0.88**

---

## Model: `claude-opus-4-6`

- **Date**: 2026-03-14 23:39:59
- **Temperature**: 0.0
- **Reward Mode**: openenv
- **Total Time**: 609.9s
- **Trajectory**: `trajectories/browser/run_browser_openenv_final/claude-opus-4-6.json`

| Scenario | Step Rewards | Ground Truth | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| coupon_threshold_trap | 0.65 | 1.00 | 0.00 | **0.86** | 20 | 81.7s |
| stock_deplete_cancel_reorder | 0.77 | 1.00 | 0.00 | **0.91** | 14 | 50.3s |
| false_price_optimal_coupon | 0.75 | 1.00 | 0.00 | **0.90** | 9 | 36.5s |
| cross_user_cart_isolation | 0.69 | 1.00 | 0.00 | **0.88** | 19 | 64.6s |
| wishlist_move_vs_direct_add | 0.73 | 1.00 | 0.00 | **0.89** | 20 | 66.0s |
| out_of_stock_boundary | 0.58 | 1.00 | 0.00 | **0.83** | 12 | 41.6s |
| expired_coupon_cascade | 0.65 | 1.00 | 0.00 | **0.86** | 10 | 33.6s |
| review_cross_page_verify | 0.72 | 1.00 | 0.00 | **0.89** | 18 | 63.4s |
| profile_update_checkout_verify | 0.73 | 1.00 | 0.00 | **0.89** | 11 | 41.9s |
| contact_then_register_same_email | 0.64 | 1.00 | 0.00 | **0.86** | 22 | 56.3s |
| bulk_cart_ops_total_tracking | 0.79 | 1.00 | 0.00 | **0.91** | 15 | 41.7s |
| cheapest_expensive_cross_category | 0.68 | 1.00 | 0.00 | **0.87** | 15 | 32.3s |

**Average Reward: 0.88**

---

## Model: `claude-opus-4-20250514`

- **Date**: 2026-03-15 00:44:35
- **Temperature**: 0.0
- **Reward Mode**: openenv
- **Total Time**: 694.1s
- **Trajectory**: `trajectories/browser/run_browser_openenv_final/claude-opus-4-20250514.json`

| Scenario | Step Rewards | Ground Truth | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| coupon_threshold_trap | 0.70 | 1.00 | 0.00 | **0.88** | 18 | 71.9s |
| stock_deplete_cancel_reorder | 0.77 | 1.00 | 0.00 | **0.91** | 12 | 47.9s |
| false_price_optimal_coupon | 0.74 | 1.00 | 0.00 | **0.90** | 10 | 41.7s |
| cross_user_cart_isolation | 0.67 | 1.00 | 0.00 | **0.87** | 23 | 78.8s |
| wishlist_move_vs_direct_add | 0.73 | 1.00 | 0.00 | **0.89** | 20 | 68.0s |
| out_of_stock_boundary | 0.57 | 1.00 | 0.00 | **0.83** | 12 | 44.5s |
| expired_coupon_cascade | 0.64 | 1.00 | 0.00 | **0.86** | 12 | 46.6s |
| review_cross_page_verify | 0.72 | 1.00 | 0.00 | **0.89** | 19 | 61.4s |
| profile_update_checkout_verify | 0.72 | 1.00 | 0.00 | **0.89** | 12 | 45.8s |
| contact_then_register_same_email | 0.64 | 1.00 | 0.00 | **0.86** | 17 | 64.1s |
| bulk_cart_ops_total_tracking | 0.78 | 1.00 | 0.00 | **0.91** | 16 | 62.6s |
| cheapest_expensive_cross_category | 0.69 | 1.00 | 0.00 | **0.88** | 14 | 60.5s |

**Average Reward: 0.88**

---

## Model: `gpt-5`

- **Date**: 2026-03-15 01:00:38
- **Temperature**: 1.0
- **Reward Mode**: openenv
- **Total Time**: 741.7s
- **Trajectory**: `trajectories/browser/run_browser_openenv_final/gpt-5.json`

| Scenario | Step Rewards | Ground Truth | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| coupon_threshold_trap | 0.00 | 0.00 | 0.00 | **0.00** | 0 | 22.9s |
| stock_deplete_cancel_reorder | 0.74 | 1.00 | 0.00 | **0.90** | 15 | 93.8s |
| false_price_optimal_coupon | 0.74 | 1.00 | 0.00 | **0.90** | 10 | 62.3s |
| cross_user_cart_isolation | 0.67 | 1.00 | 0.00 | **0.87** | 23 | 63.5s |
| wishlist_move_vs_direct_add | 0.59 | 0.33 | 0.00 | **0.44** | 6 | 75.7s |
| out_of_stock_boundary | 0.63 | 1.00 | 0.00 | **0.85** | 10 | 68.6s |
| expired_coupon_cascade | 0.64 | 1.00 | 0.00 | **0.86** | 12 | 51.8s |
| review_cross_page_verify | 0.72 | 1.00 | 0.00 | **0.89** | 19 | 55.6s |
| profile_update_checkout_verify | 0.71 | 1.00 | 0.00 | **0.88** | 15 | 99.7s |
| contact_then_register_same_email | 0.65 | 1.00 | 0.00 | **0.86** | 15 | 72.6s |
| bulk_cart_ops_total_tracking | 0.76 | 1.00 | 0.00 | **0.91** | 17 | 58.1s |
| cheapest_expensive_cross_category | — | — | — | **ERROR** | 0 | 17.0s |

**Average Reward: 0.69**

---

