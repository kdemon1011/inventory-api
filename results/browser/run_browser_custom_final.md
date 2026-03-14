# Browser Gym — Evaluation Results

**Run ID**: `run_browser_custom_final`  
**Gym Version**: `0.1.0`

Evaluation results for the **browser** gym across different LLM models.

**Reward Mode**: `custom` — episode-level rewards from `rewards/base.py`

Each model is evaluated on the same set of scenarios. Rewards are computed by `rewards/base.py` using:
- **Structural** (0.25) — right tools called, no errors
- **Ground Truth** (0.60) — database state matches expected outcome
- **Efficiency** (0.15) — solved in reasonable steps
- **Hallucination Penalty** (-1.0) — tools say success but DB disagrees

Trajectories: `trajectories/browser/run_browser_custom_final/`

---

## Model: `gpt-5.4`

- **Date**: 2026-03-14 19:53:01
- **Temperature**: 0.0
- **Reward Mode**: custom
- **Total Time**: 208.0s
- **Trajectory**: `trajectories/browser/run_browser_custom_final/gpt-5.4.json`

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| coupon_threshold_trap | 0.95 | 1.00 | 0.35 | 0.00 | **0.89** | 17 | 26.7s |
| stock_deplete_cancel_reorder | 0.88 | 1.00 | 0.57 | 0.00 | **0.91** | 14 | 17.0s |
| false_price_optimal_coupon | 0.95 | 1.00 | 0.60 | 0.00 | **0.93** | 10 | 12.0s |
| cross_user_cart_isolation | 1.00 | 1.00 | 0.26 | 0.00 | **0.89** | 23 | 21.2s |
| wishlist_move_vs_direct_add | 0.96 | 1.00 | 0.36 | 0.00 | **0.90** | 22 | 16.2s |
| out_of_stock_boundary | 0.95 | 1.00 | 0.38 | 0.00 | **0.89** | 13 | 14.4s |
| expired_coupon_cascade | 0.95 | 1.00 | 0.42 | 0.00 | **0.90** | 12 | 12.1s |
| review_cross_page_verify | 1.00 | 1.00 | 0.32 | 0.00 | **0.90** | 19 | 20.3s |
| profile_update_checkout_verify | 0.95 | 1.00 | 0.42 | 0.00 | **0.90** | 12 | 14.0s |
| contact_then_register_same_email | 0.95 | 1.00 | 0.31 | 0.00 | **0.88** | 16 | 16.8s |
| bulk_cart_ops_total_tracking | 1.00 | 1.00 | 0.50 | 0.00 | **0.92** | 16 | 24.9s |
| cheapest_expensive_cross_category | 0.95 | 1.00 | 0.43 | 0.00 | **0.90** | 14 | 12.0s |

**Average Reward: 0.90**

---

## Model: `claude-sonnet-4-6`

- **Date**: 2026-03-14 19:57:49
- **Temperature**: 0.0
- **Reward Mode**: custom
- **Total Time**: 495.9s
- **Trajectory**: `trajectories/browser/run_browser_custom_final/claude-sonnet-4-6.json`

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| coupon_threshold_trap | 0.95 | 1.00 | 0.33 | 0.00 | **0.89** | 18 | 50.9s |
| stock_deplete_cancel_reorder | 0.91 | 1.00 | 0.57 | 0.00 | **0.91** | 14 | 36.9s |
| false_price_optimal_coupon | 0.95 | 1.00 | 0.60 | 0.00 | **0.93** | 10 | 30.6s |
| cross_user_cart_isolation | 1.00 | 1.00 | 0.25 | 0.00 | **0.89** | 24 | 56.9s |
| wishlist_move_vs_direct_add | 1.00 | 1.00 | 0.36 | 0.00 | **0.90** | 22 | 50.2s |
| out_of_stock_boundary | 0.95 | 1.00 | 0.38 | 0.00 | **0.89** | 13 | 39.9s |
| expired_coupon_cascade | 0.90 | 1.00 | 0.38 | 0.00 | **0.88** | 13 | 38.8s |
| review_cross_page_verify | 1.00 | 1.00 | 0.32 | 0.00 | **0.90** | 19 | 43.3s |
| profile_update_checkout_verify | 0.90 | 1.00 | 0.38 | 0.00 | **0.88** | 13 | 37.3s |
| contact_then_register_same_email | 0.86 | 1.00 | 0.28 | 0.00 | **0.86** | 18 | 43.7s |
| bulk_cart_ops_total_tracking | 0.96 | 1.00 | 0.53 | 0.00 | **0.92** | 15 | 33.4s |
| cheapest_expensive_cross_category | 0.95 | 1.00 | 0.43 | 0.00 | **0.90** | 14 | 33.7s |

**Average Reward: 0.90**

---

## Model: `claude-opus-4-6`

- **Date**: 2026-03-14 19:59:08
- **Temperature**: 0.0
- **Reward Mode**: custom
- **Total Time**: 574.7s
- **Trajectory**: `trajectories/browser/run_browser_custom_final/claude-opus-4-6.json`

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| coupon_threshold_trap | 0.95 | 1.00 | 0.30 | 0.00 | **0.88** | 20 | 75.9s |
| stock_deplete_cancel_reorder | 0.96 | 1.00 | 0.57 | 0.00 | **0.93** | 14 | 47.2s |
| false_price_optimal_coupon | 0.90 | 1.00 | 0.67 | 0.00 | **0.92** | 9 | 33.6s |
| cross_user_cart_isolation | 1.00 | 1.00 | 0.32 | 0.00 | **0.90** | 19 | 58.2s |
| wishlist_move_vs_direct_add | 1.00 | 1.00 | 0.40 | 0.00 | **0.91** | 20 | 48.0s |
| out_of_stock_boundary | 0.95 | 1.00 | 0.42 | 0.00 | **0.90** | 12 | 42.2s |
| expired_coupon_cascade | 0.95 | 1.00 | 0.45 | 0.00 | **0.90** | 11 | 37.0s |
| review_cross_page_verify | 1.00 | 1.00 | 0.33 | 0.00 | **0.90** | 18 | 54.1s |
| profile_update_checkout_verify | 0.90 | 1.00 | 0.42 | 0.00 | **0.89** | 12 | 46.6s |
| contact_then_register_same_email | 0.86 | 1.00 | 0.23 | 0.00 | **0.85** | 22 | 61.6s |
| bulk_cart_ops_total_tracking | 0.96 | 1.00 | 0.53 | 0.00 | **0.92** | 15 | 38.3s |
| cheapest_expensive_cross_category | 0.95 | 1.00 | 0.40 | 0.00 | **0.90** | 15 | 31.7s |

**Average Reward: 0.90**

---

## Model: `claude-opus-4-20250514`

- **Date**: 2026-03-14 20:12:14
- **Temperature**: 0.0
- **Reward Mode**: custom
- **Total Time**: 685.1s
- **Trajectory**: `trajectories/browser/run_browser_custom_final/claude-opus-4-20250514.json`

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| coupon_threshold_trap | 0.95 | 1.00 | 0.33 | 0.00 | **0.89** | 18 | 75.6s |
| stock_deplete_cancel_reorder | 0.91 | 1.00 | 0.67 | 0.00 | **0.93** | 12 | 46.1s |
| false_price_optimal_coupon | 0.95 | 1.00 | 0.60 | 0.00 | **0.93** | 10 | 40.5s |
| cross_user_cart_isolation | 1.00 | 1.00 | 0.26 | 0.00 | **0.89** | 23 | 78.4s |
| wishlist_move_vs_direct_add | 1.00 | 1.00 | 0.40 | 0.00 | **0.91** | 20 | 69.8s |
| out_of_stock_boundary | 0.95 | 1.00 | 0.42 | 0.00 | **0.90** | 12 | 47.2s |
| expired_coupon_cascade | 0.95 | 1.00 | 0.42 | 0.00 | **0.90** | 12 | 45.1s |
| review_cross_page_verify | 1.00 | 1.00 | 0.32 | 0.00 | **0.90** | 19 | 61.1s |
| profile_update_checkout_verify | 0.95 | 1.00 | 0.42 | 0.00 | **0.90** | 12 | 47.6s |
| contact_then_register_same_email | 0.90 | 1.00 | 0.29 | 0.00 | **0.87** | 17 | 59.2s |
| bulk_cart_ops_total_tracking | 1.00 | 1.00 | 0.50 | 0.00 | **0.92** | 16 | 61.9s |
| cheapest_expensive_cross_category | 0.95 | 1.00 | 0.43 | 0.00 | **0.90** | 14 | 52.3s |

**Average Reward: 0.90**

---

## Model: `gpt-5`

- **Date**: 2026-03-14 23:28:52
- **Temperature**: 1.0
- **Reward Mode**: custom
- **Total Time**: 633.9s
- **Trajectory**: `trajectories/browser/run_browser_custom_final/gpt-5.json`

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| coupon_threshold_trap | 0.57 | 0.00 | 1.00 | -1.00 | **-0.71** | 1 | 46.2s |
| stock_deplete_cancel_reorder | 0.00 | 0.00 | 0.00 | 0.00 | **0.00** | 0 | 19.7s |
| false_price_optimal_coupon | 0.95 | 1.00 | 0.60 | 0.00 | **0.93** | 10 | 52.9s |
| cross_user_cart_isolation | 0.00 | 0.25 | 0.00 | 0.00 | **0.15** | 0 | 17.5s |
| wishlist_move_vs_direct_add | 0.00 | 0.17 | 0.00 | 0.00 | **0.10** | 0 | 16.5s |
| out_of_stock_boundary | 0.95 | 1.00 | 0.38 | 0.00 | **0.89** | 13 | 100.6s |
| expired_coupon_cascade | 0.95 | 1.00 | 0.42 | 0.00 | **0.90** | 12 | 48.9s |
| review_cross_page_verify | 1.00 | 1.00 | 0.32 | 0.00 | **0.90** | 19 | 61.9s |
| profile_update_checkout_verify | 0.90 | 1.00 | 0.36 | 0.00 | **0.88** | 14 | 81.7s |
| contact_then_register_same_email | 0.86 | 1.00 | 0.26 | 0.00 | **0.85** | 19 | 79.9s |
| bulk_cart_ops_total_tracking | 1.00 | 1.00 | 0.47 | 0.00 | **0.92** | 17 | 50.4s |
| cheapest_expensive_cross_category | 1.00 | 1.00 | 0.46 | 0.00 | **0.92** | 13 | 57.5s |

**Average Reward: 0.56**

---

