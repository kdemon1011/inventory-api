/**
 * Stripe Mock Service — minimal Express server simulating Stripe's API.
 *
 * Runs on port 3001 inside Docker. All data is in-memory (Map).
 * The Payment Gateway API calls this to process payments, refunds,
 * disputes, and transfers.
 *
 * Endpoints:
 *   POST   /v1/payment_intents            — Create a payment intent
 *   POST   /v1/payment_intents/:id/confirm — Confirm a payment intent
 *   GET    /v1/payment_intents/:id        — Get payment intent details
 *   POST   /v1/refunds                    — Create a refund
 *   POST   /v1/disputes                   — Create a dispute
 *   POST   /v1/disputes/:id/close         — Resolve/close a dispute
 *   GET    /v1/disputes                   — List all disputes
 *   POST   /v1/transfers                  — Create a transfer/payout
 *   GET    /v1/transfers                  — List transfers
 *   GET    /health                        — Health check
 *   POST   /v1/webhooks/trigger           — Manually trigger a webhook
 */

const express = require("express");
const { v4: uuidv4 } = require("uuid");
const axios = require("axios");

const app = express();
app.use(express.json());

const PORT = process.env.STRIPE_MOCK_PORT || 3001;
const GATEWAY_URL = process.env.GATEWAY_URL || "http://localhost:8002";

// In-memory storage
const paymentIntents = new Map();
const refunds = new Map();
const disputes = new Map();
const transfers = new Map();

// ── Helpers ──

function generateId(prefix) {
  return `${prefix}_${uuidv4().replace(/-/g, "").substring(0, 24)}`;
}

// ────────────────────────────────────────────────
// Payment Intents
// ────────────────────────────────────────────────

app.post("/v1/payment_intents", (req, res) => {
  const { amount, currency, customer_email, description, metadata } = req.body;

  if (!amount || !currency) {
    return res.status(400).json({ error: { message: "amount and currency are required" } });
  }

  const id = generateId("pi");
  const intent = {
    id,
    object: "payment_intent",
    amount,
    currency: currency.toLowerCase(),
    status: "requires_confirmation",
    customer_email: customer_email || null,
    description: description || null,
    metadata: metadata || {},
    created: Math.floor(Date.now() / 1000),
  };

  paymentIntents.set(id, intent);
  res.status(201).json(intent);
});

app.post("/v1/payment_intents/:id/confirm", async (req, res) => {
  const intent = paymentIntents.get(req.params.id);
  if (!intent) {
    return res.status(404).json({ error: { message: `Payment intent ${req.params.id} not found` } });
  }
  if (intent.status !== "requires_confirmation") {
    return res
      .status(400)
      .json({ error: { message: `Cannot confirm intent with status '${intent.status}'` } });
  }

  // Deterministic: amounts whose last digit is 7 fail (~10%), rest succeed
  const succeeded = intent.amount % 10 !== 7;
  intent.status = succeeded ? "succeeded" : "failed";
  intent.confirmed_at = Math.floor(Date.now() / 1000);

  // Fire webhook to gateway (best-effort)
  const sessionId = req.headers["x-session-id"];
  const eventType = succeeded ? "payment_intent.succeeded" : "payment_intent.payment_failed";
  fireWebhook(eventType, intent, sessionId);

  res.json(intent);
});

app.get("/v1/payment_intents/:id", (req, res) => {
  const intent = paymentIntents.get(req.params.id);
  if (!intent) {
    return res.status(404).json({ error: { message: `Payment intent ${req.params.id} not found` } });
  }
  res.json(intent);
});

// ────────────────────────────────────────────────
// Refunds
// ────────────────────────────────────────────────

app.post("/v1/refunds", (req, res) => {
  const { payment_intent: piId, amount } = req.body;

  if (!piId) {
    return res.status(400).json({ error: { message: "payment_intent is required" } });
  }

  const intent = paymentIntents.get(piId);
  if (!intent) {
    return res.status(404).json({ error: { message: `Payment intent ${piId} not found` } });
  }
  if (intent.status !== "succeeded") {
    return res
      .status(400)
      .json({ error: { message: `Cannot refund intent with status '${intent.status}'` } });
  }

  const refundAmount = amount || intent.amount;
  const id = generateId("re");
  const refund = {
    id,
    object: "refund",
    amount: refundAmount,
    currency: intent.currency,
    payment_intent: piId,
    status: "succeeded",
    created: Math.floor(Date.now() / 1000),
  };

  refunds.set(id, refund);

  // Fire webhook
  const sessionId = req.headers["x-session-id"];
  fireWebhook("charge.refunded", { ...refund, payment_intent_data: intent }, sessionId);

  res.status(201).json(refund);
});

// ────────────────────────────────────────────────
// Disputes
// ────────────────────────────────────────────────

app.post("/v1/disputes", (req, res) => {
  const { payment_intent: piId, amount, reason } = req.body;

  if (!piId) {
    return res.status(400).json({ error: { message: "payment_intent is required" } });
  }

  const intent = paymentIntents.get(piId);
  if (!intent) {
    return res.status(404).json({ error: { message: `Payment intent ${piId} not found` } });
  }

  const disputeAmount = amount || intent.amount;
  const id = generateId("dp");
  const dispute = {
    id,
    object: "dispute",
    amount: disputeAmount,
    currency: intent.currency,
    payment_intent: piId,
    reason: reason || "general",
    status: "open",
    evidence: null,
    created: Math.floor(Date.now() / 1000),
  };

  disputes.set(id, dispute);

  // Fire webhook
  const sessionId = req.headers["x-session-id"];
  fireWebhook("charge.dispute.created", { ...dispute, payment_intent_data: intent }, sessionId);

  res.status(201).json(dispute);
});

app.post("/v1/disputes/:id/close", (req, res) => {
  const dispute = disputes.get(req.params.id);
  if (!dispute) {
    return res.status(404).json({ error: { message: `Dispute ${req.params.id} not found` } });
  }
  if (dispute.status !== "open" && dispute.status !== "under_review") {
    return res
      .status(400)
      .json({ error: { message: `Dispute already resolved: ${dispute.status}` } });
  }

  const { evidence, accept_loss } = req.body;
  dispute.evidence = evidence || null;

  if (accept_loss) {
    dispute.status = "lost";
  } else {
    // Merchant fights: 70% win, 30% lose (deterministic based on dispute amount)
    dispute.status = dispute.amount % 10 < 7 ? "won" : "lost";
  }
  dispute.resolved_at = Math.floor(Date.now() / 1000);

  // Fire webhook
  const sessionId = req.headers["x-session-id"];
  const eventType = dispute.status === "won" ? "charge.dispute.won" : "charge.dispute.lost";
  fireWebhook(eventType, dispute, sessionId);

  res.json(dispute);
});

app.get("/v1/disputes", (req, res) => {
  const all = Array.from(disputes.values());
  res.json({ data: all, count: all.length });
});

// ────────────────────────────────────────────────
// Transfers / Payouts
// ────────────────────────────────────────────────

app.post("/v1/transfers", (req, res) => {
  const { amount, destination, description } = req.body;

  if (!amount || !destination) {
    return res.status(400).json({ error: { message: "amount and destination are required" } });
  }

  const id = generateId("tr");
  const transfer = {
    id,
    object: "transfer",
    amount,
    currency: "usd",
    destination,
    description: description || null,
    status: "completed",
    created: Math.floor(Date.now() / 1000),
  };

  transfers.set(id, transfer);

  // Fire webhook
  const sessionId = req.headers["x-session-id"];
  fireWebhook("transfer.created", transfer, sessionId);

  res.status(201).json(transfer);
});

app.get("/v1/transfers", (req, res) => {
  const all = Array.from(transfers.values());
  res.json({ data: all, count: all.length });
});

// ────────────────────────────────────────────────
// Health
// ────────────────────────────────────────────────

app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "stripe-mock",
    counts: {
      payment_intents: paymentIntents.size,
      refunds: refunds.size,
      disputes: disputes.size,
      transfers: transfers.size,
    },
  });
});

// ────────────────────────────────────────────────
// Manual webhook trigger (for testing)
// ────────────────────────────────────────────────

app.post("/v1/webhooks/trigger", async (req, res) => {
  const { type, data, session_id } = req.body;
  if (!type || !data) {
    return res.status(400).json({ error: { message: "type and data are required" } });
  }
  await fireWebhook(type, data, session_id);
  res.json({ status: "triggered", type });
});

// ────────────────────────────────────────────────
// Webhook helper
// ────────────────────────────────────────────────

async function fireWebhook(type, data, sessionId) {
  try {
    const headers = { "Content-Type": "application/json" };
    if (sessionId) {
      headers["X-Session-ID"] = sessionId;
    }
    await axios.post(
      `${GATEWAY_URL}/webhooks/receive`,
      { id: generateId("evt"), type, data },
      { headers, timeout: 5000 }
    );
  } catch (err) {
    console.log(`[stripe-mock] Webhook delivery failed (${type}): ${err.message}`);
  }
}

// ── Start ──

app.listen(PORT, () => {
  console.log(`[stripe-mock] Listening on port ${PORT}`);
  console.log(`[stripe-mock] Gateway URL: ${GATEWAY_URL}`);
});
