# Payment Gateway Gym — Evaluation Comparison

Comparison of **Custom Rewards** vs **OpenEnv Transform Rewards** across all 6 models.

- **Custom Rewards**: Episode-level scoring (structural 0.25 + ground truth 0.60 + efficiency 0.15 − hallucination penalty)
- **OpenEnv Transform**: Per-step scoring (step rewards 0.40 + ground truth 0.60 − hallucination penalty)

Both runs executed on the same Docker container (`openenv-payment-gateway`) with 12 complex scenarios.

---

## Overall Summary

| Model | Custom Avg | OpenEnv Avg | Δ | Custom Time | OpenEnv Time |
|---|:---:|:---:|:---:|:---:|:---:|
| claude-opus-4-20250514 | 0.9479 | 0.8502 | -0.0977 | 561s | 1714s |
| claude-opus-4-6 | 0.9501 | 0.8508 | -0.0993 | 376s | 1575s |
| claude-sonnet-4-6 | 0.9493 | 0.9289 | -0.0204 | 369s | 373s |
| gpt-5 | 0.9481 | 0.9273 | -0.0209 | 972s | 1995s |
| gpt-5.4 | 0.9491 | 0.9295 | -0.0196 | 158s | 192s |
| o3-pro | 0.9481 | 0.8495 | -0.0986 | 3907s | 5017s |
| **MEAN** | **0.9488** | **0.8894** | **-0.0594** | | |

---

## Per-Scenario Breakdown — Custom Rewards

| Scenario | claude-opus-4-20250514 | claude-opus-4-6 | claude-sonnet-4-6 | gpt-5 | gpt-5.4 | o3-pro |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| batch_payment_selective_failure_recovery | 0.90 | 0.90 | 0.90 | 0.90 | 0.90 | 0.90 |
| cascading_payment_failure_recovery | 0.99 | 1.00 | 0.99 | 0.99 | 0.99 | 0.99 |
| dispute_won_vs_lost_balance_comparison | 0.93 | 0.93 | 0.93 | 0.93 | 0.93 | 0.93 |
| end_of_day_settlement | 0.91 | 0.91 | 0.91 | 0.91 | 0.91 | 0.91 |
| full_lifecycle_stress_test | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 |
| insufficient_balance_transfer_detection | 0.95 | 0.96 | 0.96 | 0.95 | 0.96 | 0.95 |
| multi_customer_ledger_reconciliation | 0.93 | 0.93 | 0.93 | 0.93 | 0.93 | 0.93 |
| multi_transfer_incremental_drain | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 |
| over_refund_prevention_chain | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 |
| refund_blocked_after_dispute_loss | 0.94 | 0.94 | 0.95 | 0.95 | 0.94 | 0.95 |
| refund_then_dispute_interaction | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| webhook_audit_complete_lifecycle | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

---

## Per-Scenario Breakdown — OpenEnv Transform Rewards

| Scenario | claude-opus-4-20250514 | claude-opus-4-6 | claude-sonnet-4-6 | gpt-5 | gpt-5.4 | o3-pro |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| batch_payment_selective_failure_recovery | ERR | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 |
| cascading_payment_failure_recovery | 0.91 | 0.92 | 0.91 | 0.91 | 0.91 | 0.91 |
| dispute_won_vs_lost_balance_comparison | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 |
| end_of_day_settlement | 0.96 | ERR | 0.96 | 0.94 | 0.96 | 0.96 |
| full_lifecycle_stress_test | 0.95 | 0.95 | 0.95 | 0.95 | 0.95 | 0.95 |
| insufficient_balance_transfer_detection | 0.90 | 0.91 | 0.91 | 0.90 | 0.91 | 0.91 |
| multi_customer_ledger_reconciliation | 0.96 | 0.96 | 0.96 | 0.96 | 0.96 | ERR |
| multi_transfer_incremental_drain | 0.91 | 0.91 | 0.91 | 0.91 | 0.91 | 0.91 |
| over_refund_prevention_chain | 0.91 | 0.91 | 0.91 | 0.91 | 0.91 | 0.91 |
| refund_blocked_after_dispute_loss | 0.88 | 0.88 | 0.87 | 0.88 | 0.88 | 0.88 |
| refund_then_dispute_interaction | 0.93 | 0.93 | 0.93 | 0.93 | 0.93 | 0.93 |
| webhook_audit_complete_lifecycle | 0.95 | 0.95 | 0.95 | 0.95 | 0.95 | 0.95 |

---

## Key Findings

1. **Best Model (Custom)**: `claude-opus-4-6` — 0.9501
2. **Best Model (OpenEnv)**: `gpt-5.4` — 0.9295
3. **Lowest Model (Custom)**: `claude-opus-4-20250514` — 0.9479
4. **Lowest Model (OpenEnv)**: `o3-pro` — 0.8495
5. **Mean Custom Reward**: 0.9488
6. **Mean OpenEnv Reward**: 0.8894
7. **Mean Δ (OpenEnv − Custom)**: -0.0594

### Hardest Scenarios (lowest average across models)

| Scenario | Avg Custom | Avg OpenEnv |
|---|:---:|:---:|
| batch_payment_selective_failure_recovery | 0.9006 | 0.9401 |
| end_of_day_settlement | 0.9132 | 0.9543 |
| multi_customer_ledger_reconciliation | 0.9300 | 0.9573 |

### Observation

OpenEnv transform rewards are slightly **lower** than custom rewards on average. This is expected because per-step rewards penalize intermediate failures more granularly, while custom rewards look at episode-level structural success.

---

*Generated from trajectory files in `trajectories/payment_gateway/`*
