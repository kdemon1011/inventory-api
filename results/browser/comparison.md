# Browser Gym — Reward Mode Comparison

**Gym**: Browser Gym v0.1.0  
**Date**: 2026-03-15  
**Scenarios**: 12 complex scenarios (coupon traps, stock boundaries, cross-user isolation, false premises, etc.)  
**Models**: 5 (o3-pro skipped)

---

## Overall Summary

| Model | Custom Reward | OpenEnv Transform | Δ | Notes |
|---|:---:|:---:|:---:|---|
| **gpt-5.4** | **0.90** | **0.88** | -0.02 | Fastest model (~185-208s). Consistent across both modes. |
| **claude-sonnet-4-6** | **0.90** | **0.88** | -0.02 | Strong consistency. Slightly slower (~495s). |
| **claude-opus-4-6** | **0.90** | **0.88** | -0.02 | Near-identical to sonnet. Slowest Anthropic model (~575-610s). |
| **claude-opus-4-20250514** | **0.90** | **0.88** | -0.02 | Matches opus-4-6 scores. Slowest overall (~685-694s). |
| **gpt-5** | **0.56** | **0.69** | +0.13 | Requires temperature=1. Erratic: some scenarios scored 0.0/-0.71. |

**Best Custom**: gpt-5.4, claude-sonnet-4-6, claude-opus-4-6, claude-opus-4-20250514 (all 0.90)  
**Best OpenEnv**: gpt-5.4, claude-sonnet-4-6, claude-opus-4-6, claude-opus-4-20250514 (all 0.88)  
**Worst**: gpt-5 (0.56 custom / 0.69 openenv) — temperature=1 forced, hallucinated early exits

---

## Per-Scenario Breakdown — Custom Rewards

| Scenario | gpt-5.4 | sonnet-4-6 | opus-4-6 | opus-20250514 | gpt-5 |
|---|:---:|:---:|:---:|:---:|:---:|
| coupon_threshold_trap | 0.89 | 0.89 | 0.88 | 0.89 | **-0.71** |
| stock_deplete_cancel_reorder | 0.91 | 0.91 | 0.93 | 0.93 | 0.00 |
| false_price_optimal_coupon | 0.93 | 0.93 | 0.92 | 0.93 | 0.93 |
| cross_user_cart_isolation | 0.89 | 0.89 | 0.90 | 0.89 | 0.15 |
| wishlist_move_vs_direct_add | 0.90 | 0.90 | 0.91 | 0.91 | 0.10 |
| out_of_stock_boundary | 0.89 | 0.89 | 0.90 | 0.90 | 0.89 |
| expired_coupon_cascade | 0.90 | 0.88 | 0.90 | 0.90 | 0.90 |
| review_cross_page_verify | 0.90 | 0.90 | 0.90 | 0.90 | 0.90 |
| profile_update_checkout_verify | 0.90 | 0.88 | 0.89 | 0.90 | 0.88 |
| contact_then_register_same_email | 0.88 | 0.86 | 0.85 | 0.87 | 0.85 |
| bulk_cart_ops_total_tracking | 0.92 | 0.92 | 0.92 | 0.92 | 0.92 |
| cheapest_expensive_cross_category | 0.90 | 0.90 | 0.90 | 0.90 | 0.92 |
| **AVERAGE** | **0.90** | **0.90** | **0.90** | **0.90** | **0.56** |

---

## Per-Scenario Breakdown — OpenEnv Transform Rewards

| Scenario | gpt-5.4 | sonnet-4-6 | opus-4-6 | opus-20250514 | gpt-5 |
|---|:---:|:---:|:---:|:---:|:---:|
| coupon_threshold_trap | 0.87 | 0.87 | 0.86 | 0.88 | 0.00 |
| stock_deplete_cancel_reorder | 0.90 | 0.90 | 0.91 | 0.91 | 0.90 |
| false_price_optimal_coupon | 0.90 | 0.90 | 0.90 | 0.90 | 0.90 |
| cross_user_cart_isolation | 0.87 | 0.87 | 0.88 | 0.87 | 0.87 |
| wishlist_move_vs_direct_add | 0.88 | 0.89 | 0.89 | 0.89 | 0.44 |
| out_of_stock_boundary | 0.83 | 0.81 | 0.83 | 0.83 | 0.85 |
| expired_coupon_cascade | 0.86 | 0.85 | 0.86 | 0.86 | 0.86 |
| review_cross_page_verify | 0.89 | 0.89 | 0.89 | 0.89 | 0.89 |
| profile_update_checkout_verify | 0.89 | 0.89 | 0.89 | 0.89 | 0.88 |
| contact_then_register_same_email | 0.86 | 0.85 | 0.86 | 0.86 | 0.86 |
| bulk_cart_ops_total_tracking | 0.91 | 0.91 | 0.91 | 0.91 | 0.91 |
| cheapest_expensive_cross_category | 0.88 | 0.88 | 0.87 | 0.88 | ERROR |
| **AVERAGE** | **0.88** | **0.88** | **0.88** | **0.88** | **0.69** |

---

## Key Observations

### 1. Reward Mode Difference
- **Custom rewards** (Structural 25% + Ground Truth 60% + Efficiency 15%) average **~0.90** for stable models.
- **OpenEnv transform** (Step Rewards 40% + Ground Truth 60%) average **~0.88** for stable models.
- The ~0.02 drop in OpenEnv mode is expected — per-step rewards penalize navigation and form-filling steps (which get +0.2–0.5 vs full credit in custom mode).

### 2. GPT-5 Instability
- GPT-5 requires `temperature=1` (doesn't support 0.0), making it non-deterministic.
- In custom mode, GPT-5 hallucinated early exits in 4/12 scenarios (coupon_threshold_trap: -0.71, stock_deplete: 0.00, cross_user: 0.15, wishlist: 0.10).
- In OpenEnv mode, GPT-5 failed 2/12 scenarios (coupon_threshold_trap: 0.00, cheapest_expensive: ERROR due to max_tokens).
- The hallucination penalty (-1.0) in custom mode caused the severe -0.71 score.

### 3. Trap Scenario Effectiveness
- **coupon_threshold_trap**: Most effective trap — gpt-5 scored -0.71 (custom) and 0.00 (openenv). Other models handled it at 0.86–0.89.
- **cross_user_cart_isolation**: Second most effective against gpt-5 (0.15 custom, 0.87 openenv with temp=1).
- **wishlist_move_vs_direct_add**: Third trap success (0.10 custom, 0.44 openenv for gpt-5).
- Stable models (gpt-5.4, sonnet, opus) handled all traps at ≥0.85.

### 4. Speed Comparison
| Model | Custom Time | OpenEnv Time |
|---|:---:|:---:|
| gpt-5.4 | 208s | 185s |
| claude-sonnet-4-6 | 496s | 495s |
| claude-opus-4-6 | 575s | 610s |
| claude-opus-4-20250514 | 685s | 694s |
| gpt-5 | 634s | 742s |

GPT-5.4 is **3x faster** than Anthropic Opus models with identical accuracy.

### 5. Ground Truth Pass Rates
All stable models achieved **100% ground truth** across all 12 scenarios in both modes. GPT-5 achieved 100% on 8–10 of 12 scenarios (failing on trap scenarios).

---

## Configuration

- **Docker**: `openenv-browser` image with MAX_CONCURRENT_ENVS=8
- **Parallel execution**: 3+2 model split (not all 5 simultaneously)
- **Temperature**: 0.0 for all models except gpt-5 (requires 1.0)
- **Max tokens**: default (4096)
- **o3-pro**: Skipped (per user request)

---

## Files

| File | Description |
|---|---|
| `results/browser/run_browser_custom_final.md` | Full custom rewards results (5 models) |
| `results/browser/run_browser_openenv_final.md` | Full OpenEnv transform results (5 models) |
| `trajectories/browser/run_browser_custom_final/` | Per-model JSON trajectories (custom) |
| `trajectories/browser/run_browser_openenv_final/` | Per-model JSON trajectories (openenv) |
