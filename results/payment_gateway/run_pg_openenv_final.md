# Payment_Gateway Gym — Evaluation Results

**Run ID**: `run_pg_openenv_final`  
**Gym Version**: `0.1.0`

Evaluation results for the **payment_gateway** gym across different LLM models.

**Reward Mode**: `openenv` — per-step rewards from `rewards/transforms/` + ground truth

Each model is evaluated on the same set of scenarios. Rewards are computed using OpenEnv transforms:
- **Step Rewards** (0.40) — per-step success/failure from transform
- **Ground Truth** (0.60) — database state matches expected outcome
- **Hallucination Penalty** (-1.0) — tools say success but DB disagrees

Trajectories: `trajectories/payment_gateway/run_pg_openenv_final/`

---

## Model: `claude-opus-4-20250514`

- **Date**: 2026-03-14T09:25:30.659627+05:30
- **Temperature**: 0.0
- **Reward Mode**: openenv
- **Total Time**: 1713.8s
- **Trajectory**: `trajectories/payment_gateway/run_pg_openenv_final/claude-opus-4-20250514.json`

| Scenario | Step Rewards | Ground Truth | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| cascading_payment_failure_recovery | 0.77 | 1.00 | 0.00 | **0.91** | 6 | 29.6s |
| multi_customer_ledger_reconciliation | 0.89 | 1.00 | 0.00 | **0.96** | 15 | 56.5s |
| insufficient_balance_transfer_detection | 0.76 | 1.00 | 0.00 | **0.90** | 8 | 28.9s |
| refund_then_dispute_interaction | 0.83 | 1.00 | 0.00 | **0.93** | 8 | 33.1s |
| over_refund_prevention_chain | 0.79 | 1.00 | 0.00 | **0.91** | 9 | 35.9s |
| webhook_audit_complete_lifecycle | 0.88 | 1.00 | 0.00 | **0.95** | 9 | 39.5s |
| batch_payment_selective_failure_recovery | — | — | — | **ERROR** | 0 | 0.0s |
| end_of_day_settlement | 0.89 | 1.00 | 0.00 | **0.96** | 19 | 201.3s |
| dispute_won_vs_lost_balance_comparison | 0.85 | 1.00 | 0.00 | **0.94** | 11 | 47.0s |
| refund_blocked_after_dispute_loss | 0.70 | 1.00 | 0.00 | **0.88** | 10 | 46.2s |
| multi_transfer_incremental_drain | 0.77 | 1.00 | 0.00 | **0.91** | 10 | 40.2s |
| full_lifecycle_stress_test | 0.87 | 1.00 | 0.00 | **0.95** | 20 | 79.4s |

**Average Reward: 0.85**

---

## Model: `claude-opus-4-6`

- **Date**: 2026-03-14T09:23:10.971120+05:30
- **Temperature**: 0.0
- **Reward Mode**: openenv
- **Total Time**: 1575.1s
- **Trajectory**: `trajectories/payment_gateway/run_pg_openenv_final/claude-opus-4-6.json`

| Scenario | Step Rewards | Ground Truth | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| cascading_payment_failure_recovery | 0.80 | 1.00 | 0.00 | **0.92** | 7 | 31.4s |
| multi_customer_ledger_reconciliation | 0.89 | 1.00 | 0.00 | **0.96** | 15 | 38.5s |
| insufficient_balance_transfer_detection | 0.77 | 1.00 | 0.00 | **0.91** | 7 | 27.2s |
| refund_then_dispute_interaction | 0.83 | 1.00 | 0.00 | **0.93** | 8 | 27.3s |
| over_refund_prevention_chain | 0.79 | 1.00 | 0.00 | **0.91** | 9 | 35.7s |
| webhook_audit_complete_lifecycle | 0.88 | 1.00 | 0.00 | **0.95** | 9 | 33.8s |
| batch_payment_selective_failure_recovery | 0.85 | 1.00 | 0.00 | **0.94** | 14 | 30.7s |
| end_of_day_settlement | — | — | — | **ERROR** | 0 | 0.0s |
| dispute_won_vs_lost_balance_comparison | 0.85 | 1.00 | 0.00 | **0.94** | 11 | 168.9s |
| refund_blocked_after_dispute_loss | 0.70 | 1.00 | 0.00 | **0.88** | 10 | 30.7s |
| multi_transfer_incremental_drain | 0.79 | 1.00 | 0.00 | **0.91** | 9 | 32.2s |
| full_lifecycle_stress_test | 0.87 | 1.00 | 0.00 | **0.95** | 20 | 42.6s |

**Average Reward: 0.85**

---

## Model: `claude-sonnet-4-6`

- **Date**: 2026-03-14T08:56:28.599791+05:30
- **Temperature**: 0.0
- **Reward Mode**: openenv
- **Total Time**: 372.8s
- **Trajectory**: `trajectories/payment_gateway/run_pg_openenv_final/claude-sonnet-4-6.json`

| Scenario | Step Rewards | Ground Truth | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| cascading_payment_failure_recovery | 0.77 | 1.00 | 0.00 | **0.91** | 6 | 25.0s |
| multi_customer_ledger_reconciliation | 0.89 | 1.00 | 0.00 | **0.96** | 15 | 33.4s |
| insufficient_balance_transfer_detection | 0.77 | 1.00 | 0.00 | **0.91** | 7 | 23.6s |
| refund_then_dispute_interaction | 0.83 | 1.00 | 0.00 | **0.93** | 8 | 20.6s |
| over_refund_prevention_chain | 0.79 | 1.00 | 0.00 | **0.91** | 9 | 31.9s |
| webhook_audit_complete_lifecycle | 0.88 | 1.00 | 0.00 | **0.95** | 9 | 31.7s |
| batch_payment_selective_failure_recovery | 0.85 | 1.00 | 0.00 | **0.94** | 14 | 28.2s |
| end_of_day_settlement | 0.89 | 1.00 | 0.00 | **0.96** | 19 | 37.5s |
| dispute_won_vs_lost_balance_comparison | 0.85 | 1.00 | 0.00 | **0.94** | 11 | 28.4s |
| refund_blocked_after_dispute_loss | 0.68 | 1.00 | 0.00 | **0.87** | 9 | 29.3s |
| multi_transfer_incremental_drain | 0.79 | 1.00 | 0.00 | **0.91** | 9 | 31.3s |
| full_lifecycle_stress_test | 0.87 | 1.00 | 0.00 | **0.95** | 20 | 51.6s |

**Average Reward: 0.93**

---

## Model: `gpt-5.4`

- **Date**: 2026-03-14T08:53:26.465771+05:30
- **Temperature**: 0.0
- **Reward Mode**: openenv
- **Total Time**: 191.6s
- **Trajectory**: `trajectories/payment_gateway/run_pg_openenv_final/gpt-5.4.json`

| Scenario | Step Rewards | Ground Truth | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| cascading_payment_failure_recovery | 0.77 | 1.00 | 0.00 | **0.91** | 6 | 20.8s |
| multi_customer_ledger_reconciliation | 0.89 | 1.00 | 0.00 | **0.96** | 15 | 18.7s |
| insufficient_balance_transfer_detection | 0.77 | 1.00 | 0.00 | **0.91** | 7 | 12.0s |
| refund_then_dispute_interaction | 0.83 | 1.00 | 0.00 | **0.93** | 8 | 15.9s |
| over_refund_prevention_chain | 0.79 | 1.00 | 0.00 | **0.91** | 9 | 13.6s |
| webhook_audit_complete_lifecycle | 0.88 | 1.00 | 0.00 | **0.95** | 9 | 20.6s |
| batch_payment_selective_failure_recovery | 0.85 | 1.00 | 0.00 | **0.94** | 14 | 12.3s |
| end_of_day_settlement | 0.89 | 1.00 | 0.00 | **0.96** | 19 | 16.5s |
| dispute_won_vs_lost_balance_comparison | 0.85 | 1.00 | 0.00 | **0.94** | 11 | 15.9s |
| refund_blocked_after_dispute_loss | 0.70 | 1.00 | 0.00 | **0.88** | 10 | 13.2s |
| multi_transfer_incremental_drain | 0.79 | 1.00 | 0.00 | **0.91** | 9 | 12.9s |
| full_lifecycle_stress_test | 0.87 | 1.00 | 0.00 | **0.95** | 20 | 18.9s |

**Average Reward: 0.93**

---

## Model: `gpt-5`

- **Date**: 2026-03-14T09:30:10.125173+05:30
- **Temperature**: 0.0
- **Reward Mode**: openenv
- **Total Time**: 1995.3s
- **Trajectory**: `trajectories/payment_gateway/run_pg_openenv_final/gpt-5.json`

| Scenario | Step Rewards | Ground Truth | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| cascading_payment_failure_recovery | 0.77 | 1.00 | 0.00 | **0.91** | 6 | 98.9s |
| multi_customer_ledger_reconciliation | 0.89 | 1.00 | 0.00 | **0.96** | 15 | 74.9s |
| insufficient_balance_transfer_detection | 0.76 | 1.00 | 0.00 | **0.90** | 8 | 39.9s |
| refund_then_dispute_interaction | 0.83 | 1.00 | 0.00 | **0.93** | 8 | 1252.2s |
| over_refund_prevention_chain | 0.79 | 1.00 | 0.00 | **0.91** | 9 | 69.8s |
| webhook_audit_complete_lifecycle | 0.88 | 1.00 | 0.00 | **0.95** | 9 | 49.6s |
| batch_payment_selective_failure_recovery | 0.84 | 1.00 | 0.00 | **0.94** | 15 | 103.4s |
| end_of_day_settlement | 0.85 | 1.00 | 0.00 | **0.94** | 20 | 71.2s |
| dispute_won_vs_lost_balance_comparison | 0.85 | 1.00 | 0.00 | **0.94** | 11 | 28.9s |
| refund_blocked_after_dispute_loss | 0.70 | 1.00 | 0.00 | **0.88** | 9 | 66.9s |
| multi_transfer_incremental_drain | 0.79 | 1.00 | 0.00 | **0.91** | 9 | 46.0s |
| full_lifecycle_stress_test | 0.87 | 1.00 | 0.00 | **0.95** | 20 | 93.3s |

**Average Reward: 0.93**

---

## Model: `o3-pro`

- **Date**: 2026-03-14T10:17:03.530606+05:30
- **Temperature**: 0.0
- **Reward Mode**: openenv
- **Total Time**: 5017.1s
- **Trajectory**: `trajectories/payment_gateway/run_pg_openenv_final/o3-pro.json`

| Scenario | Step Rewards | Ground Truth | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| cascading_payment_failure_recovery | 0.77 | 1.00 | 0.00 | **0.91** | 6 | 138.1s |
| multi_customer_ledger_reconciliation | — | — | — | **ERROR** | 0 | 0.0s |
| insufficient_balance_transfer_detection | 0.77 | 1.00 | 0.00 | **0.91** | 7 | 196.7s |
| refund_then_dispute_interaction | 0.83 | 1.00 | 0.00 | **0.93** | 8 | 314.1s |
| over_refund_prevention_chain | 0.79 | 1.00 | 0.00 | **0.91** | 9 | 411.7s |
| webhook_audit_complete_lifecycle | 0.88 | 1.00 | 0.00 | **0.95** | 9 | 222.7s |
| batch_payment_selective_failure_recovery | 0.85 | 1.00 | 0.00 | **0.94** | 16 | 265.6s |
| end_of_day_settlement | 0.89 | 1.00 | 0.00 | **0.96** | 19 | 320.8s |
| dispute_won_vs_lost_balance_comparison | 0.85 | 1.00 | 0.00 | **0.94** | 11 | 218.2s |
| refund_blocked_after_dispute_loss | 0.70 | 1.00 | 0.00 | **0.88** | 9 | 159.1s |
| multi_transfer_incremental_drain | 0.77 | 1.00 | 0.00 | **0.91** | 10 | 179.0s |
| full_lifecycle_stress_test | 0.87 | 1.00 | 0.00 | **0.95** | 20 | 483.2s |

**Average Reward: 0.85**

---

