# Payment_Gateway Gym — Evaluation Results

**Run ID**: `run_pg_custom_final`  
**Gym Version**: `0.1.0`

Evaluation results for the **payment_gateway** gym across different LLM models.

**Reward Mode**: `custom` — episode-level rewards from `rewards/base.py`

Each model is evaluated on the same set of scenarios. Rewards are computed by `rewards/base.py` using:
- **Structural** (0.25) — right tools called, no errors
- **Ground Truth** (0.60) — database state matches expected outcome
- **Efficiency** (0.15) — solved in reasonable steps
- **Hallucination Penalty** (-1.0) — tools say success but DB disagrees

Trajectories: `trajectories/payment_gateway/run_pg_custom_final/`

---

## Model: `claude-opus-4-20250514`

- **Date**: 2026-03-14T00:16:57.938483+05:30
- **Temperature**: 0.0
- **Reward Mode**: custom
- **Total Time**: 561.2s
- **Trajectory**: `trajectories/payment_gateway/run_pg_custom_final/claude-opus-4-20250514.json`

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| cascading_payment_failure_recovery | 0.95 | 1.00 | 1.00 | 0.00 | **0.99** | 6 | 32.4s |
| multi_customer_ledger_reconciliation | 1.00 | 1.00 | 0.53 | 0.00 | **0.93** | 15 | 61.1s |
| insufficient_balance_transfer_detection | 0.95 | 1.00 | 0.75 | 0.00 | **0.95** | 8 | 33.0s |
| refund_then_dispute_interaction | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 8 | 32.5s |
| over_refund_prevention_chain | 0.96 | 1.00 | 0.67 | 0.00 | **0.94** | 9 | 39.8s |
| webhook_audit_complete_lifecycle | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 9 | 39.4s |
| batch_payment_selective_failure_recovery | 0.95 | 1.00 | 0.43 | 0.00 | **0.90** | 14 | 54.1s |
| end_of_day_settlement | 1.00 | 1.00 | 0.42 | 0.00 | **0.91** | 19 | 67.5s |
| dispute_won_vs_lost_balance_comparison | 1.00 | 1.00 | 0.55 | 0.00 | **0.93** | 11 | 46.1s |
| refund_blocked_after_dispute_loss | 0.89 | 1.00 | 0.80 | 0.00 | **0.94** | 10 | 38.1s |
| multi_transfer_incremental_drain | 0.96 | 1.00 | 0.67 | 0.00 | **0.94** | 9 | 35.3s |
| full_lifecycle_stress_test | 1.00 | 1.00 | 0.60 | 0.00 | **0.94** | 20 | 81.6s |

**Average Reward: 0.95**

---

## Model: `claude-opus-4-6`

- **Date**: 2026-03-14T00:13:50.875608+05:30
- **Temperature**: 0.0
- **Reward Mode**: custom
- **Total Time**: 376.1s
- **Trajectory**: `trajectories/payment_gateway/run_pg_custom_final/claude-opus-4-6.json`

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| cascading_payment_failure_recovery | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 7 | 26.7s |
| multi_customer_ledger_reconciliation | 1.00 | 1.00 | 0.53 | 0.00 | **0.93** | 15 | 33.0s |
| insufficient_balance_transfer_detection | 0.94 | 1.00 | 0.86 | 0.00 | **0.96** | 7 | 28.5s |
| refund_then_dispute_interaction | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 8 | 25.8s |
| over_refund_prevention_chain | 0.96 | 1.00 | 0.67 | 0.00 | **0.94** | 9 | 30.4s |
| webhook_audit_complete_lifecycle | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 9 | 34.1s |
| batch_payment_selective_failure_recovery | 0.95 | 1.00 | 0.43 | 0.00 | **0.90** | 14 | 29.9s |
| end_of_day_settlement | 1.00 | 1.00 | 0.42 | 0.00 | **0.91** | 19 | 38.8s |
| dispute_won_vs_lost_balance_comparison | 1.00 | 1.00 | 0.55 | 0.00 | **0.93** | 11 | 28.2s |
| refund_blocked_after_dispute_loss | 0.89 | 1.00 | 0.80 | 0.00 | **0.94** | 10 | 27.7s |
| multi_transfer_incremental_drain | 0.96 | 1.00 | 0.67 | 0.00 | **0.94** | 9 | 28.2s |
| full_lifecycle_stress_test | 1.00 | 1.00 | 0.60 | 0.00 | **0.94** | 20 | 44.6s |

**Average Reward: 0.95**

---

## Model: `claude-sonnet-4-6`

- **Date**: 2026-03-14T00:13:42.409532+05:30
- **Temperature**: 0.0
- **Reward Mode**: custom
- **Total Time**: 368.6s
- **Trajectory**: `trajectories/payment_gateway/run_pg_custom_final/claude-sonnet-4-6.json`

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| cascading_payment_failure_recovery | 0.95 | 1.00 | 1.00 | 0.00 | **0.99** | 6 | 25.3s |
| multi_customer_ledger_reconciliation | 1.00 | 1.00 | 0.53 | 0.00 | **0.93** | 15 | 36.9s |
| insufficient_balance_transfer_detection | 0.94 | 1.00 | 0.86 | 0.00 | **0.96** | 7 | 25.0s |
| refund_then_dispute_interaction | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 8 | 25.1s |
| over_refund_prevention_chain | 0.96 | 1.00 | 0.67 | 0.00 | **0.94** | 9 | 33.4s |
| webhook_audit_complete_lifecycle | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 9 | 28.4s |
| batch_payment_selective_failure_recovery | 0.95 | 1.00 | 0.43 | 0.00 | **0.90** | 14 | 25.2s |
| end_of_day_settlement | 1.00 | 1.00 | 0.42 | 0.00 | **0.91** | 19 | 33.8s |
| dispute_won_vs_lost_balance_comparison | 1.00 | 1.00 | 0.55 | 0.00 | **0.93** | 11 | 27.5s |
| refund_blocked_after_dispute_loss | 0.85 | 1.00 | 0.89 | 0.00 | **0.95** | 9 | 29.1s |
| multi_transfer_incremental_drain | 0.96 | 1.00 | 0.67 | 0.00 | **0.94** | 9 | 30.5s |
| full_lifecycle_stress_test | 1.00 | 1.00 | 0.60 | 0.00 | **0.94** | 20 | 48.0s |

**Average Reward: 0.95**

---

## Model: `gpt-5.4`

- **Date**: 2026-03-14T00:10:10.699820+05:30
- **Temperature**: 0.0
- **Reward Mode**: custom
- **Total Time**: 157.9s
- **Trajectory**: `trajectories/payment_gateway/run_pg_custom_final/gpt-5.4.json`

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| cascading_payment_failure_recovery | 0.95 | 1.00 | 1.00 | 0.00 | **0.99** | 6 | 15.6s |
| multi_customer_ledger_reconciliation | 1.00 | 1.00 | 0.53 | 0.00 | **0.93** | 15 | 15.6s |
| insufficient_balance_transfer_detection | 0.94 | 1.00 | 0.86 | 0.00 | **0.96** | 7 | 9.3s |
| refund_then_dispute_interaction | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 8 | 10.9s |
| over_refund_prevention_chain | 0.96 | 1.00 | 0.67 | 0.00 | **0.94** | 9 | 11.8s |
| webhook_audit_complete_lifecycle | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 9 | 13.5s |
| batch_payment_selective_failure_recovery | 0.95 | 1.00 | 0.43 | 0.00 | **0.90** | 14 | 10.7s |
| end_of_day_settlement | 1.00 | 1.00 | 0.42 | 0.00 | **0.91** | 19 | 15.2s |
| dispute_won_vs_lost_balance_comparison | 1.00 | 1.00 | 0.55 | 0.00 | **0.93** | 11 | 12.0s |
| refund_blocked_after_dispute_loss | 0.89 | 1.00 | 0.80 | 0.00 | **0.94** | 10 | 12.1s |
| multi_transfer_incremental_drain | 0.96 | 1.00 | 0.67 | 0.00 | **0.94** | 9 | 11.8s |
| full_lifecycle_stress_test | 1.00 | 1.00 | 0.60 | 0.00 | **0.94** | 20 | 19.0s |

**Average Reward: 0.95**

---

## Model: `gpt-5`

- **Date**: 2026-03-14T00:23:49.484340+05:30
- **Temperature**: 0.0
- **Reward Mode**: custom
- **Total Time**: 971.7s
- **Trajectory**: `trajectories/payment_gateway/run_pg_custom_final/gpt-5.json`

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| cascading_payment_failure_recovery | 0.95 | 1.00 | 1.00 | 0.00 | **0.99** | 6 | 115.1s |
| multi_customer_ledger_reconciliation | 1.00 | 1.00 | 0.53 | 0.00 | **0.93** | 15 | 104.8s |
| insufficient_balance_transfer_detection | 0.95 | 1.00 | 0.75 | 0.00 | **0.95** | 8 | 58.5s |
| refund_then_dispute_interaction | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 8 | 58.0s |
| over_refund_prevention_chain | 0.96 | 1.00 | 0.67 | 0.00 | **0.94** | 9 | 73.6s |
| webhook_audit_complete_lifecycle | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 9 | 61.7s |
| batch_payment_selective_failure_recovery | 0.95 | 1.00 | 0.43 | 0.00 | **0.90** | 14 | 122.7s |
| end_of_day_settlement | 1.00 | 1.00 | 0.42 | 0.00 | **0.91** | 19 | 81.5s |
| dispute_won_vs_lost_balance_comparison | 1.00 | 1.00 | 0.55 | 0.00 | **0.93** | 11 | 45.8s |
| refund_blocked_after_dispute_loss | 0.85 | 1.00 | 0.89 | 0.00 | **0.95** | 9 | 98.0s |
| multi_transfer_incremental_drain | 0.96 | 1.00 | 0.67 | 0.00 | **0.94** | 9 | 46.8s |
| full_lifecycle_stress_test | 1.00 | 1.00 | 0.60 | 0.00 | **0.94** | 20 | 104.9s |

**Average Reward: 0.95**

---

## Model: `o3-pro`

- **Date**: 2026-03-14T01:12:42.607408+05:30
- **Temperature**: 0.0
- **Reward Mode**: custom
- **Total Time**: 3906.8s
- **Trajectory**: `trajectories/payment_gateway/run_pg_custom_final/o3-pro.json`

| Scenario | Structural | Ground Truth | Efficiency | Penalty | **Total** | Steps | Time |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| cascading_payment_failure_recovery | 0.95 | 1.00 | 1.00 | 0.00 | **0.99** | 6 | 172.8s |
| multi_customer_ledger_reconciliation | 1.00 | 1.00 | 0.53 | 0.00 | **0.93** | 15 | 382.9s |
| insufficient_balance_transfer_detection | 0.95 | 1.00 | 0.75 | 0.00 | **0.95** | 8 | 172.4s |
| refund_then_dispute_interaction | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 8 | 221.9s |
| over_refund_prevention_chain | 0.96 | 1.00 | 0.67 | 0.00 | **0.94** | 9 | 239.1s |
| webhook_audit_complete_lifecycle | 1.00 | 1.00 | 1.00 | 0.00 | **1.00** | 9 | 256.8s |
| batch_payment_selective_failure_recovery | 0.95 | 1.00 | 0.43 | 0.00 | **0.90** | 14 | 499.1s |
| end_of_day_settlement | 1.00 | 1.00 | 0.42 | 0.00 | **0.91** | 19 | 417.7s |
| dispute_won_vs_lost_balance_comparison | 1.00 | 1.00 | 0.55 | 0.00 | **0.93** | 11 | 244.0s |
| refund_blocked_after_dispute_loss | 0.85 | 1.00 | 0.89 | 0.00 | **0.95** | 9 | 219.7s |
| multi_transfer_incremental_drain | 0.96 | 1.00 | 0.67 | 0.00 | **0.94** | 9 | 458.4s |
| full_lifecycle_stress_test | 1.00 | 1.00 | 0.60 | 0.00 | **0.94** | 20 | 621.8s |

**Average Reward: 0.95**

---

