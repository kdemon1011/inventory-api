# Browser Gym

Full-stack e-commerce web application (Node.js + React) wrapped as an [OpenEnv](https://github.com/meta-pytorch/OpenEnv) MCP environment. The agent navigates pages, clicks elements, fills forms, and asserts DOM state — all through 15 browser-like MCP tools via the OpenEnv API.

## Architecture

```
┌─────────────────┐         ┌──────────────────────┐         ┌──────────────────────────┐
│  LLM Agent      │         │  OpenEnv Server      │         │  Web App                 │
│  (run_eval.py)  │ ──WS──► │  (Python, port 9003) │ ──HTTP─►│  Express API (port 8003) │
│                 │ ◄────── │  MCPEnvironment      │ ◄────── │  + React SPA (served)    │
└─────────────────┘         │  15 browser-like     │         │  + SQLite DB             │
                            │  MCP tools           │         └──────────────────────────┘
                            └──────────────────────┘
```

### Flow

1. **LLM Agent** connects to the OpenEnv server via WebSocket (`ws://localhost:9003/ws`)
2. Agent calls `list_tools()` → OpenEnv returns 15 browser-like MCP tools
3. Agent reasons about the task and decides which tool to call (navigate, click, fill, submit, etc.)
4. Agent sends `env.step(CallToolAction(...))` → OpenEnv executes the tool
5. The tool (inside `browser_environment.py`) makes HTTP calls to the Express API
6. Result flows back: Express API → Environment → Agent
7. After all steps, the reward system queries the Express API's internal endpoints to verify ground truth

The LLM **never calls the Express API directly**. All interactions go through OpenEnv via `env.step()`.

### Concurrent Sessions

Multiple models can evaluate **simultaneously** against a single Docker container. Each session gets its own isolated SQLite database:

```
┌───────────────────────── Single Docker Container ─────────────────────────┐
│                                                                            │
│  OpenEnv Server (port 9003)              Express API (port 8003)           │
│  ┌─────────────────────────┐             ┌─────────────────────────┐       │
│  │ WS /ws  ──► Env inst 1  │──── HTTP ──►│  X-Session-ID: abc-123  │──► data/sessions/abc-123.db │
│  │ WS /ws  ──► Env inst 2  │──── HTTP ──►│  X-Session-ID: def-456  │──► data/sessions/def-456.db │
│  │ WS /ws  ──► Env inst 3  │──── HTTP ──►│  X-Session-ID: ghi-789  │──► data/sessions/ghi-789.db │
│  └─────────────────────────┘             └─────────────────────────┘       │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

- **`SUPPORTS_CONCURRENT_SESSIONS = True`** in the environment class allows OpenEnv to create multiple `BrowserEnvironment` instances
- Each `env.reset()` creates a unique session ID and requests an isolated DB via `POST /api/sessions`
- All subsequent HTTP calls include `X-Session-ID` header → Express routes to the correct session DB
- Ground truth checker is session-aware — it queries the session-specific DB
- Session DBs are automatically deleted when the environment closes

## Files

| File | Role | OpenEnv Class |
|---|---|---|
| `server/browser_environment.py` | 15 browser-like MCP tools + `get_session_info` | `MCPEnvironment` |
| `server/app.py` | Auto-generated server (HTTP + WebSocket) | `create_app()` |
| `Dockerfile` | Docker image (Express + React + OpenEnv in one container) | — |
| `client.py` | Client + AutoEnv type aliases | `MCPToolClient` |
| `openenv.yaml` | Environment manifest | — |
| `pyproject.toml` | Package config (validate / build / uv run) | — |
| `.env` | All configuration (ports, concurrency) | — |
| `webapp/server.js` | Express API + serves React SPA + session management | — |
| `webapp/db/setup.js` | SQLite schema + seed data (15 products, 3 coupons, 2 users) | — |
| `webapp/routes/*.js` | Express route modules (auth, products, cart, orders, etc.) | — |

## Running the Gym

### Step 0: Install for AutoEnv discovery (one-time)

```bash
# From the repo root
pip install -e browser/
```

Verify:
```bash
python -c "from openenv import AutoEnv; AutoEnv.list_environments()"
```

### Start the Gym (Docker)

Docker packages the Express app, React SPA, and OpenEnv server into a single container:

```bash
# 1. Build the image (from this directory)
docker build -t openenv-browser .

# 2. Run the container
#    Port 8003 = Express API + React SPA
#    Port 9003 = OpenEnv server (AutoEnv connects here)
docker run -d --name browser -p 8003:8003 -p 9003:9003 openenv-browser

# 3. Verify both servers are ready
curl http://localhost:9003/health    # → {"status": "healthy"}
curl http://localhost:9003/metadata  # → {"name": "browser_gym", "version": "0.1.0", ...}
curl http://localhost:8003/health    # → {"status": "ok", "service": "browser-gym-webapp"}
curl http://localhost:8003/api/products  # → {"products": [...], "total": 15}

# 4. Run an evaluation
cd ..  # repo root
python run_eval.py --gym browser --model gpt-5.4 --save --trajectory

# 4b. Or run multiple models in parallel
python run_eval.py --gym browser \
  --model gpt-5.4,claude-sonnet-4-6,claude-opus-4-6 \
  --parallel 3 --save --trajectory

# 5. Stop and remove when done
docker stop browser && docker rm browser
```

### Override Concurrency

```bash
docker run -d --name browser -p 8003:8003 -p 9003:9003 \
  -e MAX_CONCURRENT_ENVS=8 openenv-browser
```

## Available Tools (15)

| # | Tool | Description |
|---|------|-------------|
| 1 | `get_session_info` | Returns the current session ID (infrastructure, not for agent use) |
| 2 | `navigate` | Navigate to a page by route (e.g., `/products`, `/login`). Returns page content as JSON |
| 3 | `get_page_content` | Re-read the current page's content as structured JSON |
| 4 | `click_element` | Click an element by its identifier (button ID, link text) |
| 5 | `fill_form` | Fill a form field by name with a value |
| 6 | `submit_form` | Submit the current form on the page |
| 7 | `search_products` | Search for products by query string |
| 8 | `get_element_text` | Get the text content of a specific element by ID |
| 9 | `add_to_cart` | Add a product to cart by product ID and quantity |
| 10 | `update_cart_item` | Update quantity of a cart item |
| 11 | `remove_from_cart` | Remove an item from the cart |
| 12 | `get_cart` | Get current cart contents with totals |
| 13 | `checkout` | Complete checkout with shipping details and optional coupon |
| 14 | `toggle_wishlist` | Add/remove a product from the wishlist |
| 15 | `assert_text_visible` | Assert that specific text is visible on the current page |

## Reward Modes

Two reward modes, both sharing the same ground truth checker (`rewards/browser_checks.py`).

```bash
# Default: episode-level reward
python run_eval.py --gym browser --model gpt-5.4 --reward-mode custom

# OpenEnv per-step reward
python run_eval.py --gym browser --model gpt-5.4 --reward-mode openenv
```

### Custom Rewards (`--reward-mode custom`)

Calculated **after the episode ends** by `rewards/base.py → RewardCalculator`:

| Component | Weight | Calculation |
|---|---|---|
| **Structural** | 0.25 | `0.6 × F1(expected_tools, used_tools) + 0.4 × success_rate` |
| **Ground Truth** | 0.60 | `passed_checks / total_checks` (queries Express API internal endpoints) |
| **Efficiency** | 0.15 | `min(expected_steps / actual_steps, 1.0)` |
| **Penalty** | -1.0 | If all steps succeed but 0 ground truth checks pass (hallucination) |

**Total** = `0.25 × structural + 0.60 × ground_truth + 0.15 × efficiency + penalty`

### OpenEnv Transform Rewards (`--reward-mode openenv`)

Calculated **per-step** by `rewards/transforms/browser.py → BrowserStepTransform`, then combined with ground truth by `OpenEnvRewardCalculator`:

| Component | Weight | Calculation |
|---|---|---|
| **Step Rewards** | 0.40 | Avg per-step reward, normalized to [0, 1] |
| **Ground Truth** | 0.60 | `passed_checks / total_checks` (same DB verification) |
| **Penalty** | -1.0 | If all step rewards > 0 but 0 ground truth checks pass |

The `BrowserStepTransform` scores each tool call by action significance:

| Tool Category | Reward | Examples |
|---|---|---|
| Major mutations | **+1.0** | `checkout`, `submit_form` (login, register, review) |
| Cart/wishlist modifications | **+0.8** | `add_to_cart`, `remove_from_cart`, `toggle_wishlist` |
| Navigation/search | **+0.5** | `navigate`, `search_products`, `click_element` |
| Assertions (visible=true) | **+0.8** | `assert_text_visible` when text is found |
| Assertions (visible=false) | **+0.3** | `assert_text_visible` when text is not found |
| Read/infrastructure | **+0.1 to +0.3** | `get_cart`, `get_page_content`, `fill_form`, `get_session_info` |
| Any error | **-0.5** | Tool call failed or returned `{"error": ...}` |

## Scenarios (12)

All 12 scenarios in `scenarios/browser.py` are **complex** — designed to challenge SOTA models with multi-step chains, cross-page reasoning, false premises, and numerical traps.

| # | ID | Trap / Failure Mode | Checks |
|---|---|---|---|
| 1 | `coupon_threshold_trap` | Coupon fails on first attempt (subtotal < $100 min), model must recover by adding items | 6 |
| 2 | `stock_deplete_cancel_reorder` | Stock lifecycle: buy last copy → cancel → verify restock → rebuy | 5 |
| 3 | `false_price_optimal_coupon` | FALSE premise in prompt ("cheapest book is $15") — model must verify real prices | 5 |
| 4 | `cross_user_cart_isolation` | Switch users mid-scenario — cart must NOT leak between accounts | 8 |
| 5 | `wishlist_move_vs_direct_add` | Wishlist "move-to-cart" side effects vs direct "add-to-cart" difference | 6 |
| 6 | `out_of_stock_boundary` | Product has stock=1, add qty=2 (should fail), recover with qty=1 | 6 |
| 7 | `expired_coupon_cascade` | EXPIRED → invalid code → correct coupon — 3 failure-recovery cycles | 6 |
| 8 | `review_cross_page_verify` | Post review → navigate away → return → verify review persisted | 7 |
| 9 | `profile_update_checkout_verify` | Update profile address → verify it propagates to order shipping | 7 |
| 10 | `contact_then_register_same_email` | Contact form without auth → register same email → verify both entities | 6 |
| 11 | `bulk_cart_ops_total_tracking` | 7+ cart operations with precise total verification at each step | 6 |
| 12 | `cheapest_expensive_cross_category` | Search + sort + cross-category cart assembly with exact arithmetic | 6 |

Each scenario uses unique emails (`sc{N}@browser.test`) to prevent cross-scenario conflicts when run in parallel.

## Ground Truth Verification

The `BrowserChecker` (`rewards/browser_checks.py`) queries 6 internal verification endpoints on the Express API to check database state directly:

| Check Type | Verifies |
|---|---|
| `user_exists` / `user_field` | User registration and profile updates |
| `order_exists` / `order_count` / `order_status` / `order_total` / `order_discount` / `order_coupon` / `order_item_count` / `order_shipping` | Order lifecycle |
| `cart_count` | Cart state |
| `wishlist_count` | Wishlist state |
| `product_stock` | Inventory tracking |
| `review_exists` / `review_rating` | Review submissions |
| `contact_exists` | Contact form submissions |

## Configuration

All configuration is in `.env`:

```env
# Node.js web app (Express + React SPA)
WEBAPP_PORT=8003
WEBAPP_URL=http://localhost:8003

# OpenEnv server (Python)
OPENENV_PORT=9003

# Concurrent sessions (max parallel evaluations)
MAX_CONCURRENT_ENVS=8
```

API keys for LLM providers are in the root `.env` file:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Seed Data

| Category | Products | Price Range |
|---|---|---|
| Electronics (4) | USB-C Hub, Mechanical Keyboard, Noise-Cancelling Headphones, 4K Monitor | $34.99 – $349.99 |
| Clothing (4) | Cotton T-Shirt, Denim Jacket, Wool Beanie, Running Shoes | $14.99 – $89.99 |
| Books (4) | JavaScript: The Good Parts, Clean Code, Design Patterns, The Pragmatic Programmer | $29.99 – $44.99 |
| Home (3) | Ceramic Plant Pot, Desk Lamp, Throw Blanket | $18.99 – $34.99 |

**Coupons:** `SAVE10` (10% off, min $50), `SAVE20` (20% off, min $100), `EXPIRED01` (inactive)
**Pre-seeded users:** Alice (`alice@example.com`), Bob (`bob@example.com`)
