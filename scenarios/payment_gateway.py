"""
Scenario definitions for the Payment Gateway gym.

Each scenario describes a COMPLEX multi-step task that an LLM agent must complete
via OpenEnv MCP tools. All 12 scenarios require multi-tool chains, cross-entity
reasoning, balance verification, and error handling.

Scenarios use unique email prefixes (sc1- through sc12-) to prevent conflicts
during concurrent evaluation.

Complexity techniques that challenge SOTA models:
  - Deterministic payment failures (amounts ending in 7 cents → fail on confirm)
  - Balance arithmetic across payments, refunds, disputes, and transfers
  - Cross-entity state verification (dispute loss changes payment status)
  - Error handling requirements (over-refund, insufficient balance for transfers)
  - Refund-blocked-after-dispute-loss trap
  - Asymmetric dispute outcomes (won keeps money, lost deducts)
  - Batch operations requiring careful state tracking across many IDs
  - Implicit reasoning (prompts describe outcomes, model must plan tool sequence)

12 scenarios, all complex. Target: < 0.7 average score on SOTA models.
"""

from rewards.base import Scenario


PAYMENT_GATEWAY_SCENARIOS = [
    # ══════════════════════════════════════════════════════════════════
    # 1. Cascading Payment Failure & Recovery
    #
    # Trap: $100.07 = 10007 cents → last digit 7 → deterministic failure
    #       Model must detect failure from confirm result, not assume success.
    #       Must retry with a DIFFERENT amount (not the same failing amount).
    # ══════════════════════════════════════════════════════════════════
    Scenario(
        id="cascading_payment_failure_recovery",
        prompt=(
            "A new customer named 'Dana Chen' needs to be onboarded with email "
            "'sc1-dana@test.com'. Once registered, process a payment of exactly "
            "$100.07 USD for this customer and attempt to confirm it. "
            "After confirmation, inspect the payment status — if the payment "
            "failed during processing, retry the payment using an amount of "
            "$100.00 USD instead. Verify the retry succeeded, then confirm that "
            "the account balance reflects exactly one successful payment of "
            "$100.00. Also check that both a failure and a success webhook were "
            "delivered."
        ),
        expected_tools=[
            "create_customer", "create_payment", "confirm_payment",
            "get_payment", "retry_payment", "get_balance", "list_webhooks",
        ],
        max_steps=12,
        outcome_checks=[
            {"type": "customer_exists", "email": "sc1-dana@test.com"},
            {"type": "payment_status", "customer_email": "sc1-dana@test.com", "status": "failed"},
            {"type": "payment_status", "customer_email": "sc1-dana@test.com", "status": "succeeded"},
            {"type": "balance_equals", "amount": 10000},
            {"type": "webhook_received", "event_type": "payment_intent.payment_failed"},
            {"type": "webhook_received", "event_type": "payment_intent.succeeded"},
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # 2. Multi-Customer Ledger Reconciliation
    #
    # Trap: dispute-won has ZERO balance impact (counterintuitive).
    #       Model must track 3 customers × different adjustments.
    #       Partial refund, full refund, and fought dispute — all different.
    # ══════════════════════════════════════════════════════════════════
    Scenario(
        id="multi_customer_ledger_reconciliation",
        prompt=(
            "Set up three customers and process their payments:\n"
            "  • 'Alice Park' (sc2-alice@test.com) — $150.00 payment\n"
            "  • 'Bob Lee' (sc2-bob@test.com) — $250.00 payment\n"
            "  • 'Carol Ng' (sc2-carol@test.com) — $350.00 payment\n\n"
            "Confirm all three payments. Then apply these adjustments:\n"
            "  1. Partial refund of $75.00 from Alice's payment\n"
            "  2. Full refund of Bob's entire $250.00 payment\n"
            "  3. Open a dispute on Carol's payment for $100.00 (reason: "
            "'product_not_received') and fight it with evidence: "
            "'Delivery confirmed — tracking #CP-887291 signed at door'\n\n"
            "After all adjustments, verify the total account balance and "
            "audit the webhook trail to confirm all events were recorded."
        ),
        expected_tools=[
            "create_customer", "create_payment", "confirm_payment",
            "create_refund", "create_dispute", "resolve_dispute",
            "get_balance", "list_webhooks",
        ],
        max_steps=20,
        outcome_checks=[
            {"type": "customer_exists", "email": "sc2-alice@test.com"},
            {"type": "customer_exists", "email": "sc2-bob@test.com"},
            {"type": "customer_exists", "email": "sc2-carol@test.com"},
            {"type": "dispute_status", "customer_email": "sc2-carol@test.com", "status": "won"},
            # Balance: $150-75 + $250-250 + $350-0(won) = $425
            {"type": "balance_equals", "amount": 42500},
            {"type": "webhook_received", "event_type": "payment_intent.succeeded"},
            {"type": "webhook_received", "event_type": "charge.refunded"},
            {"type": "webhook_count_gte", "count": 5},
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # 3. Insufficient Balance Transfer Detection
    #
    # Trap: after refund only $50 remains, but transfer requests $100.
    #       Model must handle the transfer rejection gracefully and retry
    #       with the correct remaining amount. Many models hallucinate
    #       transfer success without checking the error response.
    # ══════════════════════════════════════════════════════════════════
    Scenario(
        id="insufficient_balance_transfer_detection",
        prompt=(
            "Register customer 'Eva Ruiz' (sc3-eva@test.com) and process a "
            "$200.00 USD payment. Confirm the payment, then issue a $150.00 "
            "refund. Now attempt to transfer $100.00 to destination account "
            "'acct_vendor_99'. The transfer will be rejected for insufficient "
            "funds — only $50.00 remains in the balance. Handle the error and "
            "transfer the correct remaining amount of $50.00 to the same "
            "vendor account. Confirm the final balance is exactly $0.00."
        ),
        expected_tools=[
            "create_customer", "create_payment", "confirm_payment",
            "create_refund", "create_transfer", "get_balance",
        ],
        max_steps=12,
        outcome_checks=[
            {"type": "customer_exists", "email": "sc3-eva@test.com"},
            {"type": "refund_exists", "customer_email": "sc3-eva@test.com"},
            {"type": "transfer_exists", "destination": "acct_vendor_99"},
            {"type": "transfer_amount", "destination": "acct_vendor_99", "amount": 5000},
            {"type": "balance_equals", "amount": 0},
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # 4. Refund-Then-Dispute on Same Payment
    #
    # Trap: partial refund does NOT change payment status (stays "succeeded"),
    #       so a dispute CAN still be opened. But the dispute loss changes
    #       payment status to "refunded". Both deductions stack.
    #       Model must understand the interaction: $500 - $200(refund) -
    #       $200(dispute lost) = $100.
    # ══════════════════════════════════════════════════════════════════
    Scenario(
        id="refund_then_dispute_interaction",
        prompt=(
            "Register customer 'Frank Hsu' (sc4-frank@test.com) and process a "
            "$500.00 payment. Confirm it. Then perform these operations on the "
            "SAME payment:\n"
            "  1. Issue a partial refund of $200.00\n"
            "  2. Open a dispute for $200.00 with reason 'fraudulent'\n"
            "  3. Accept the dispute loss\n\n"
            "After resolving the dispute, verify the payment's current status "
            "and the account balance. The balance should reflect both the "
            "refund deduction and the dispute loss: $500 - $200 - $200 = $100.00."
        ),
        expected_tools=[
            "create_customer", "create_payment", "confirm_payment",
            "create_refund", "create_dispute", "resolve_dispute",
            "get_payment", "get_balance",
        ],
        max_steps=15,
        outcome_checks=[
            {"type": "customer_exists", "email": "sc4-frank@test.com"},
            {"type": "refund_exists", "customer_email": "sc4-frank@test.com"},
            {"type": "dispute_status", "customer_email": "sc4-frank@test.com", "status": "lost"},
            {"type": "payment_status", "customer_email": "sc4-frank@test.com", "status": "refunded"},
            # Balance: $500 - $200(refund) - $200(dispute lost) = $100
            {"type": "balance_equals", "amount": 10000},
            {"type": "webhook_received", "event_type": "charge.dispute.lost"},
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # 5. Over-Refund Prevention Chain
    #
    # Trap: three $120 refunds on a $300 payment. First two succeed,
    #       third FAILS (only $60 remaining). Model must catch the
    #       error and adjust to the correct remaining amount.
    #       Tests: arithmetic reasoning + error recovery in a loop.
    # ══════════════════════════════════════════════════════════════════
    Scenario(
        id="over_refund_prevention_chain",
        prompt=(
            "Register customer 'Grace Kim' (sc5-grace@test.com) and process a "
            "$300.00 payment. Confirm the payment. Now issue three sequential "
            "partial refunds of $120.00 each. The first two should succeed, but "
            "the third will be rejected because only $60.00 remains refundable. "
            "Handle the rejection by issuing a final $60.00 refund to bring the "
            "payment to a full refund. Verify by listing all refunds to see "
            "exactly 3 successful refunds ($120 + $120 + $60), and confirm the "
            "balance is $0.00."
        ),
        expected_tools=[
            "create_customer", "create_payment", "confirm_payment",
            "create_refund", "list_refunds", "get_balance",
        ],
        max_steps=14,
        outcome_checks=[
            {"type": "customer_exists", "email": "sc5-grace@test.com"},
            {"type": "refund_exists", "customer_email": "sc5-grace@test.com"},
            {"type": "balance_equals", "amount": 0},
            {"type": "webhook_received", "event_type": "charge.refunded"},
            {"type": "webhook_count_gte", "count": 4},
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # 6. Complete Lifecycle Webhook Audit
    #
    # Trap: model must perform a full lifecycle AND then verify that
    #       SPECIFIC webhook event types were delivered. Requires listing
    #       webhooks and cross-referencing types — not just acting.
    #       Missing any operation means missing a webhook type.
    # ══════════════════════════════════════════════════════════════════
    Scenario(
        id="webhook_audit_complete_lifecycle",
        prompt=(
            "Register customer 'Henry Wang' (sc6-henry@test.com) and execute "
            "a complete payment lifecycle:\n"
            "  1. Process an $800.00 payment and confirm it\n"
            "  2. Issue a $200.00 partial refund\n"
            "  3. Open a dispute for $300.00 (reason: 'product_not_received'), "
            "fight it with evidence: 'Delivered per tracking #HD-928374'\n"
            "  4. Transfer $200.00 to 'acct_settlement_main'\n\n"
            "After all operations, list all webhook events and verify that "
            "EVERY one of these event types was delivered:\n"
            "  • payment_intent.succeeded\n"
            "  • charge.refunded\n"
            "  • charge.dispute.created\n"
            "  • charge.dispute.won\n"
            "  • transfer.created\n\n"
            "Also verify the final balance: $800 - $200(refund) - $0(dispute "
            "won) - $200(transfer) = $400.00."
        ),
        expected_tools=[
            "create_customer", "create_payment", "confirm_payment",
            "create_refund", "create_dispute", "resolve_dispute",
            "create_transfer", "list_webhooks", "get_balance",
        ],
        max_steps=16,
        outcome_checks=[
            {"type": "customer_exists", "email": "sc6-henry@test.com"},
            {"type": "balance_equals", "amount": 40000},
            {"type": "webhook_received", "event_type": "payment_intent.succeeded"},
            {"type": "webhook_received", "event_type": "charge.refunded"},
            {"type": "webhook_received", "event_type": "charge.dispute.created"},
            {"type": "webhook_received", "event_type": "charge.dispute.won"},
            {"type": "webhook_received", "event_type": "transfer.created"},
            {"type": "webhook_count_gte", "count": 5},
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # 7. Batch Payment with Selective Failure Recovery
    #
    # Trap: 5 payments, 2 fail silently (cents ending in 7).
    #       Model must track 5 separate payment IDs, check each
    #       confirmation result, identify the 2 failures, retry with
    #       corrected amounts, and calculate the final balance.
    #       Most models lose track of IDs in batch operations.
    # ══════════════════════════════════════════════════════════════════
    Scenario(
        id="batch_payment_selective_failure_recovery",
        prompt=(
            "Register customer 'Iris Tanaka' (sc7-iris@test.com). Process five "
            "separate payments for this customer with these exact USD amounts:\n"
            "  Payment A: $100.00\n"
            "  Payment B: $50.07\n"
            "  Payment C: $200.00\n"
            "  Payment D: $75.17\n"
            "  Payment E: $300.00\n\n"
            "Confirm each payment after creation. Check every confirmation "
            "result — some payments will fail during processing. For any "
            "payment that failed, retry it with a rounded-down dollar amount "
            "(drop the cents, e.g. $50.07 → $50.00, $75.17 → $75.00). After "
            "all retries succeed, verify the final account balance matches "
            "the sum of all successful payments."
        ),
        expected_tools=[
            "create_customer", "create_payment", "confirm_payment",
            "retry_payment", "list_payments", "get_balance",
        ],
        max_steps=22,
        outcome_checks=[
            {"type": "customer_exists", "email": "sc7-iris@test.com"},
            # At least one payment should have failed (the originals)
            {"type": "payment_status", "customer_email": "sc7-iris@test.com", "status": "failed"},
            # At least one succeeded
            {"type": "payment_status", "customer_email": "sc7-iris@test.com", "status": "succeeded"},
            # Balance: $100 + $50 + $200 + $75 + $300 = $725.00
            {"type": "balance_equals", "amount": 72500},
            {"type": "webhook_received", "event_type": "payment_intent.payment_failed"},
            {"type": "webhook_received", "event_type": "payment_intent.succeeded"},
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # 8. End-of-Day Multi-Customer Settlement
    #
    # Trap: 3 customers, 5 payments, mixed adjustments. Jack has TWO
    #       payments — model must refund from the LARGER one ($400, not
    #       $100). Dispute loss on Leo's FIRST payment, not the second.
    #       Balance math is the hardest: $1225 - $50 - $250 - $300 - $200
    #       = $425. Most models get the attribution wrong.
    # ══════════════════════════════════════════════════════════════════
    Scenario(
        id="end_of_day_settlement",
        prompt=(
            "Process an end-of-day settlement batch:\n\n"
            "Customers:\n"
            "  • 'Jack Rivera' (sc8-jack@test.com)\n"
            "  • 'Kate Bergström' (sc8-kate@test.com)\n"
            "  • 'Leo Okafor' (sc8-leo@test.com)\n\n"
            "Payments:\n"
            "  • Jack: two payments — $400.00 and $100.00\n"
            "  • Kate: one payment — $250.00\n"
            "  • Leo: two payments — $300.00 and $175.00\n\n"
            "Confirm all five payments. Then apply adjustments:\n"
            "  1. Refund $50.00 from Jack's LARGER payment (the $400 one)\n"
            "  2. Full refund of Kate's $250.00 payment\n"
            "  3. Dispute Leo's FIRST payment ($300.00) for the full amount, "
            "reason 'duplicate', and accept the loss\n"
            "  4. Transfer $200.00 to 'acct_daily_settlement'\n\n"
            "Report the final balance. Expected calculation:\n"
            "  Total payments: $400 + $100 + $250 + $300 + $175 = $1,225.00\n"
            "  Minus refunds: $50 + $250 = $300.00\n"
            "  Minus dispute loss: $300.00\n"
            "  Minus transfer: $200.00\n"
            "  Final balance: $425.00"
        ),
        expected_tools=[
            "create_customer", "create_payment", "confirm_payment",
            "create_refund", "create_dispute", "resolve_dispute",
            "create_transfer", "get_balance",
        ],
        max_steps=28,
        outcome_checks=[
            {"type": "customer_exists", "email": "sc8-jack@test.com"},
            {"type": "customer_exists", "email": "sc8-kate@test.com"},
            {"type": "customer_exists", "email": "sc8-leo@test.com"},
            {"type": "dispute_status", "customer_email": "sc8-leo@test.com", "status": "lost"},
            {"type": "transfer_exists", "destination": "acct_daily_settlement"},
            {"type": "transfer_amount", "destination": "acct_daily_settlement", "amount": 20000},
            # Balance: $1225 - $50 - $250 - $300(dispute) - $200(transfer) = $425
            {"type": "balance_equals", "amount": 42500},
            {"type": "webhook_count_gte", "count": 7},
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # 9. Dispute Won vs Lost — Balance Asymmetry
    #
    # Trap: identical setups, different dispute resolutions.
    #       Won dispute → merchant keeps the money (no deduction).
    #       Lost dispute → forced refund (deducted from balance).
    #       Model must understand the asymmetry and verify that the
    #       balance only decreases for the lost dispute.
    # ══════════════════════════════════════════════════════════════════
    Scenario(
        id="dispute_won_vs_lost_balance_comparison",
        prompt=(
            "Register two customers to compare dispute outcomes:\n\n"
            "Customer 1 — 'Maya Singh' (sc9-maya@test.com):\n"
            "  Process and confirm a $400.00 payment. Open a dispute for "
            "$150.00 (reason: 'product_not_received'). FIGHT the dispute "
            "with evidence: 'Package delivered and signed for, proof attached.'\n\n"
            "Customer 2 — 'Noah Fischer' (sc9-noah@test.com):\n"
            "  Process and confirm a $400.00 payment. Open a dispute for "
            "$150.00 (reason: 'fraudulent'). ACCEPT the loss on this dispute.\n\n"
            "After both disputes are resolved, check the balance. Maya's "
            "dispute (won) should NOT reduce the balance — her full $400 "
            "remains. Noah's dispute (lost) SHOULD reduce it by $150. "
            "Expected total balance: $800.00 - $150.00 = $650.00."
        ),
        expected_tools=[
            "create_customer", "create_payment", "confirm_payment",
            "create_dispute", "resolve_dispute", "get_balance",
        ],
        max_steps=16,
        outcome_checks=[
            {"type": "customer_exists", "email": "sc9-maya@test.com"},
            {"type": "customer_exists", "email": "sc9-noah@test.com"},
            {"type": "dispute_status", "customer_email": "sc9-maya@test.com", "status": "won"},
            {"type": "dispute_status", "customer_email": "sc9-noah@test.com", "status": "lost"},
            {"type": "payment_status", "customer_email": "sc9-maya@test.com", "status": "succeeded"},
            {"type": "payment_status", "customer_email": "sc9-noah@test.com", "status": "refunded"},
            # Balance: $400(won→no loss) + $400-$150(lost) = $650
            {"type": "balance_equals", "amount": 65000},
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # 10. Refund Blocked After Dispute Loss
    #
    # Trap: dispute loss changes payment status to "refunded".
    #       Subsequent refund attempt MUST fail (status != "succeeded").
    #       Model must attempt the refund, handle the rejection, and
    #       verify the balance WITHOUT the refund. Most models either
    #       skip the refund attempt or hallucinate its success.
    # ══════════════════════════════════════════════════════════════════
    Scenario(
        id="refund_blocked_after_dispute_loss",
        prompt=(
            "Register customer 'Olivia Petrov' (sc10-olivia@test.com) and "
            "process a $600.00 payment. Confirm it. Open a dispute for "
            "$250.00 with reason 'product_not_received' and accept the loss.\n\n"
            "After the dispute resolves, the payment's status will have "
            "changed. Now attempt to issue a $100.00 refund on this same "
            "payment. The refund should be REJECTED because the payment is "
            "no longer in a refundable state.\n\n"
            "Verify: the dispute resolved as 'lost', the refund was NOT "
            "created (there should be no successful refunds), and the "
            "balance is $600.00 - $250.00 = $350.00."
        ),
        expected_tools=[
            "create_customer", "create_payment", "confirm_payment",
            "create_dispute", "resolve_dispute", "create_refund",
            "get_payment", "get_balance",
        ],
        max_steps=14,
        outcome_checks=[
            {"type": "customer_exists", "email": "sc10-olivia@test.com"},
            {"type": "dispute_status", "customer_email": "sc10-olivia@test.com", "status": "lost"},
            {"type": "payment_status", "customer_email": "sc10-olivia@test.com", "status": "refunded"},
            # Balance: $600 - $250(dispute loss) = $350  (no refund because it was blocked)
            {"type": "balance_equals", "amount": 35000},
            {"type": "webhook_received", "event_type": "charge.dispute.lost"},
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # 11. Multi-Transfer Incremental Balance Drain
    #
    # Trap: three $200 transfers on a $500 balance. Third one fails
    #       (only $100 remaining). Model must track running balance
    #       across sequential transfers and adjust the final amount.
    #       Tests: sequential state tracking + error recovery.
    # ══════════════════════════════════════════════════════════════════
    Scenario(
        id="multi_transfer_incremental_drain",
        prompt=(
            "Register customer 'Paul Zhang' (sc11-paul@test.com) and process "
            "a $500.00 payment. Confirm it. Execute the following three "
            "transfers in sequence:\n"
            "  1. $200.00 to 'acct_partner_alpha'\n"
            "  2. $200.00 to 'acct_partner_beta'\n"
            "  3. $200.00 to 'acct_partner_gamma'\n\n"
            "The third transfer will be rejected because only $100.00 remains "
            "in the balance. Handle the rejection by transferring the correct "
            "remaining amount ($100.00) to 'acct_partner_gamma' instead. "
            "Verify the final balance is $0.00 and list all transfers to "
            "confirm three successful transfers with correct amounts."
        ),
        expected_tools=[
            "create_customer", "create_payment", "confirm_payment",
            "create_transfer", "list_transfers", "get_balance",
        ],
        max_steps=15,
        outcome_checks=[
            {"type": "customer_exists", "email": "sc11-paul@test.com"},
            {"type": "transfer_exists", "destination": "acct_partner_alpha"},
            {"type": "transfer_amount", "destination": "acct_partner_alpha", "amount": 20000},
            {"type": "transfer_exists", "destination": "acct_partner_beta"},
            {"type": "transfer_amount", "destination": "acct_partner_beta", "amount": 20000},
            {"type": "transfer_exists", "destination": "acct_partner_gamma"},
            {"type": "transfer_amount", "destination": "acct_partner_gamma", "amount": 10000},
            {"type": "balance_equals", "amount": 0},
        ],
    ),

    # ══════════════════════════════════════════════════════════════════
    # 12. Full Lifecycle Stress Test
    #
    # Maximum complexity: 3 customers, payment failure + retry,
    # customer update, partial refund, fought dispute, transfer,
    # and comprehensive verification. Designed to overwhelm context
    # windows with many entity IDs and interleaved operations.
    #
    # Traps:
    #   - Sam's $300.07 = 30007 cents → ends in 7 → FAILS
    #   - Model must detect failure and retry with $300.00
    #   - Must update Rachel's name AFTER creating her (not at creation)
    #   - Dispute on Tara's FIRST payment, not the second
    #   - Balance: $500+$300+$450+$200 - $150 - $0(won) - $100 = $1200
    # ══════════════════════════════════════════════════════════════════
    Scenario(
        id="full_lifecycle_stress_test",
        prompt=(
            "Execute a comprehensive payment gateway stress test:\n\n"
            "1. Register three customers:\n"
            "   • 'Rachel Torres' (sc12-rachel@test.com)\n"
            "   • 'Sam Nakamura' (sc12-sam@test.com)\n"
            "   • 'Tara Johansson' (sc12-tara@test.com)\n\n"
            "2. Process payments:\n"
            "   • Rachel: $500.00\n"
            "   • Sam: $300.07 (note this exact amount)\n"
            "   • Tara: $450.00 AND $200.00 (two separate payments)\n\n"
            "3. Confirm all four payments. Sam's payment may fail during "
            "processing — if it does, retry it with $300.00.\n\n"
            "4. Update Rachel's customer name to 'Rachel Torres-Vega'.\n\n"
            "5. Adjustments:\n"
            "   • Partial refund $150.00 from Rachel's payment\n"
            "   • Dispute Tara's FIRST payment ($450.00) for $200.00, "
            "reason 'duplicate', fight with evidence: 'Only one charge "
            "verified — receipt #TV-9981'\n"
            "   • Transfer $100.00 to 'acct_ops_reserve'\n\n"
            "6. Final checks: verify balance, list customers to confirm "
            "Rachel's name was updated, and audit all webhooks."
        ),
        expected_tools=[
            "create_customer", "create_payment", "confirm_payment",
            "retry_payment", "update_customer", "create_refund",
            "create_dispute", "resolve_dispute", "create_transfer",
            "get_balance", "list_customers", "list_webhooks",
        ],
        max_steps=30,
        outcome_checks=[
            {"type": "customer_exists", "email": "sc12-rachel@test.com"},
            {"type": "customer_exists", "email": "sc12-sam@test.com"},
            {"type": "customer_exists", "email": "sc12-tara@test.com"},
            {"type": "customer_name", "email": "sc12-rachel@test.com", "expected_name": "Rachel Torres-Vega"},
            {"type": "refund_exists", "customer_email": "sc12-rachel@test.com"},
            {"type": "dispute_status", "customer_email": "sc12-tara@test.com", "status": "won"},
            {"type": "transfer_exists", "destination": "acct_ops_reserve"},
            {"type": "transfer_amount", "destination": "acct_ops_reserve", "amount": 10000},
            # Balance: $500+$300+$450+$200 = $1450
            #   - $150(refund) - $0(dispute won) - $100(transfer) = $1200
            {"type": "balance_equals", "amount": 120000},
            {"type": "webhook_received", "event_type": "payment_intent.payment_failed"},
            {"type": "webhook_count_gte", "count": 7},
        ],
    ),
]
