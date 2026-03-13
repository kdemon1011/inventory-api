# Payment Gateway Gym

A Stripe-like payment processing environment for OpenEnv. The agent interacts with 18 MCP tools covering the full payment lifecycle: customer management, payment processing, refunds, disputes/chargebacks, transfers/payouts, balance tracking, and webhook auditing.

## Architecture

```
┌─────────────────┐         ┌──────────────────────┐         ┌──────────────────┐         ┌──────────┐
│  LLM Agent      │         │  OpenEnv Server      │         │  Payment Gateway │         │  SQLite  │
│  (run_eval.py)  │ ──WS──► │  (port 9002)         │ ──HTTP─►│  API (port 8002) │ ──────► │  DB      │
│                 │ ◄────── │  MCPEnvironment      │ ◄────── │  FastAPI         │ ◄────── │          │
└─────────────────┘         └──────────────────────┘         └──────────────────┘         └──────────┘
                                                                      │
                                                                      │ HTTP (webhooks + API)
                                                                      ▼
                                                              ┌──────────────────┐
                                                              │  Stripe Mock     │
                                                              │  (port 3001)     │
                                                              │  Node.js/Express │
                                                              └──────────────────┘
```

## Services

| Service | Port | Language | Purpose |
|---------|------|----------|---------|
| Stripe Mock | 3001 | Node.js (Express) | Simulates Stripe API — payment intents, refunds, disputes, transfers, webhooks |
| Payment Gateway API | 8002 | Python (FastAPI) | Business logic — customers, payments, refunds, disputes, transfers, balance, DB |
| OpenEnv Server | 9002 | Python (OpenEnv) | MCP tool server — agent interface |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/customers` | Create a customer |
| GET | `/customers` | List all customers |
| GET | `/customers/{id}` | Get customer by ID |
| PATCH | `/customers/{id}` | Update customer details |
| POST | `/payments` | Create a payment intent |
| POST | `/payments/{id}/confirm` | Confirm a payment intent |
| GET | `/payments` | List payments (filterable by status) |
| GET | `/payments/{id}` | Get payment details |
| POST | `/refunds` | Create a refund |
| GET | `/refunds` | List all refunds |
| POST | `/disputes` | Open a dispute/chargeback |
| POST | `/disputes/{id}/resolve` | Submit evidence and resolve dispute |
| GET | `/disputes` | List disputes (filterable by status) |
| POST | `/transfers` | Create a transfer/payout |
| GET | `/transfers` | List all transfers |
| POST | `/webhooks/receive` | Receive webhook from Stripe mock |
| GET | `/webhooks` | List webhook events |
| GET | `/balance` | Get account balance summary |
| GET | `/health` | Health check |
| POST | `/sessions` | Create evaluation session |
| GET | `/sessions` | List active sessions |
| DELETE | `/sessions/{id}` | Delete session |

## Available MCP Tools (18)

| # | Tool | Category | Description |
|---|------|----------|-------------|
| 1 | `get_session_info` | Infrastructure | Returns session_id for DB isolation |
| 2 | `create_customer` | Customers | Register a new customer |
| 3 | `get_customer` | Customers | Get customer details by ID |
| 4 | `list_customers` | Customers | List all registered customers |
| 5 | `update_customer` | Customers | Update customer name/phone |
| 6 | `create_payment` | Payments | Create a payment intent |
| 7 | `confirm_payment` | Payments | Confirm a pending payment |
| 8 | `get_payment` | Payments | Get payment details by ID |
| 9 | `list_payments` | Payments | List payments (filterable by status) |
| 10 | `retry_payment` | Payments | Retry a failed payment |
| 11 | `create_refund` | Refunds | Refund a payment (full or partial) |
| 12 | `list_refunds` | Refunds | List all refunds |
| 13 | `create_dispute` | Disputes | Open a chargeback on a payment |
| 14 | `resolve_dispute` | Disputes | Submit evidence and resolve |
| 15 | `list_disputes` | Disputes | List disputes (filterable by status) |
| 16 | `create_transfer` | Transfers | Transfer funds from balance |
| 17 | `list_transfers` | Transfers | List all transfers |
| 18 | `get_balance` | Balance | Get balance (payments - refunds - disputes - transfers) |
| — | `list_webhooks` | Webhooks | List received webhook events |

## Running

```bash
# Build
cd payment-gateway && docker build -t openenv-payment-gateway .

# Run
docker run -d --name payment-gateway -p 8002:8002 -p 9002:9002 openenv-payment-gateway

# Verify
curl http://localhost:9002/health
curl http://localhost:9002/metadata
curl http://localhost:8002/health
curl http://localhost:8002/balance

# Evaluate
python run_eval.py --gym payment_gateway --model gpt-4o --save --trajectory

# Parallel evaluation (6 models)
python run_eval.py --gym payment_gateway \
  --model gpt-5.4,claude-sonnet-4-6,claude-opus-4-6,o3-pro,claude-opus-4-20250514,gpt-5 \
  --parallel 6 --save --trajectory

# Stop
docker stop payment-gateway && docker rm payment-gateway
```

## Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | `8002` | Payment Gateway API port |
| `DATABASE_URL` | `sqlite+aiosqlite:///data/app.db` | SQLite database path |
| `OPENENV_PORT` | `9002` | OpenEnv server port |
| `PAYMENT_API_URL` | `http://localhost:8002` | Internal API URL |
| `STRIPE_MOCK_URL` | `http://localhost:3001` | Stripe mock URL |
| `WEBHOOK_SECRET` | `whsec_test_secret_key` | Webhook signature secret |
| `MAX_CONCURRENT_ENVS` | `4` | Max parallel evaluation sessions |

## Concurrent Sessions

Each evaluation session gets an isolated SQLite database. Multiple agents can evaluate simultaneously without interfering with each other's payment/customer/dispute state.

```
Agent 1 → Session abc-123 → data/sessions/abc-123.db
Agent 2 → Session def-456 → data/sessions/def-456.db
```

## Data Models

| Model | Table | Key Fields |
|-------|-------|------------|
| Customer | `customers` | email (unique), name, phone, address |
| PaymentIntent | `payment_intents` | stripe_id, amount, currency, status, customer_email |
| Refund | `refunds` | payment_intent_id, amount, status |
| Dispute | `disputes` | payment_intent_id, amount, status, reason, evidence |
| Transfer | `transfers` | amount, destination, status |
| WebhookEvent | `webhook_events` | event_type, payload, processed |
