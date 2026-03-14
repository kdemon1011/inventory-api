/**
 * Browser Gym — Express API Server
 *
 * Serves:
 *   - REST API at /api/*
 *   - Session management via X-Session-ID header → per-session SQLite DB
 *   - /api/page/:route — returns page structure as JSON for browser-like MCP tools
 *   - React SPA from dist/ (static files)
 *   - Health check at /health
 */

const express = require("express");
const path = require("path");
const { openDb, createSession, deleteSession } = require("./db/setup");

const app = express();
const PORT = process.env.WEBAPP_PORT || 8003;

app.use(express.json());

// ── Session + Auth middleware ──
// Attaches req.db (session-scoped SQLite) and req.userId (from auth token)
app.use((req, res, next) => {
  const sessionId = req.headers["x-session-id"] || null;
  req.db = openDb(sessionId);
  req.sessionId = sessionId;

  // Parse auth token (base64-encoded user ID)
  const auth = req.headers["authorization"];
  if (auth && auth.startsWith("Bearer ")) {
    try {
      req.userId = parseInt(Buffer.from(auth.slice(7), "base64").toString());
    } catch {
      req.userId = null;
    }
  } else {
    req.userId = null;
  }

  // Close DB after response
  res.on("finish", () => {
    try { req.db.close(); } catch {}
  });

  next();
});

// ── Session management endpoints (called by OpenEnv BrowserEnvironment) ──
app.post("/api/sessions", (req, res) => {
  const { session_id } = req.body;
  if (!session_id) return res.status(400).json({ error: "session_id required" });
  createSession(session_id);
  res.status(201).json({ session_id, created: true });
});

app.delete("/api/sessions/:id", (req, res) => {
  deleteSession(req.params.id);
  res.json({ session_id: req.params.id, deleted: true });
});

// ── API routes ──
app.use("/api/auth", require("./routes/auth"));
app.use("/api/products", require("./routes/products"));
app.use("/api/cart", require("./routes/cart"));
app.use("/api/orders", require("./routes/orders"));
app.use("/api/wishlist", require("./routes/wishlist"));
app.use("/api/profile", require("./routes/profile"));
app.use("/api/contact", require("./routes/contact"));
app.use("/api/coupons", require("./routes/coupons"));

// ── /api/page/:route — Returns page structure as JSON for browser-like navigation ──
// This is the key endpoint that MCP tools use to "see" the page.
app.get("/api/page/*", (req, res) => {
  const route = "/" + (req.params[0] || "");
  const db = req.db;

  try {
    const page = buildPageContent(route, db, req.userId);
    res.json(page);
  } catch (e) {
    res.status(404).json({ error: `Page not found: ${route}` });
  }
});

/**
 * Build a structured JSON representation of a page.
 * This is what the agent "sees" when it navigates.
 */
function buildPageContent(route, db, userId) {
  // Home / Products listing
  if (route === "/" || route === "/home") {
    const featured = db.prepare("SELECT id, name, price, category, stock FROM products ORDER BY RANDOM() LIMIT 6").all();
    const categories = db.prepare("SELECT DISTINCT category FROM products").all().map(r => r.category);
    return {
      page: "home",
      title: "Welcome to BrowserGym Shop",
      elements: {
        nav: { links: ["Home", "Products", "Cart", "Orders", "Wishlist", "Profile", "Contact", "Login", "Register"] },
        search_bar: { id: "search-input", placeholder: "Search products..." },
        featured_products: featured,
        categories,
      },
    };
  }

  // Login
  if (route === "/login") {
    return {
      page: "login",
      title: "Login",
      elements: {
        form: {
          id: "login-form",
          fields: [
            { name: "email", type: "email", label: "Email", required: true },
            { name: "password", type: "password", label: "Password", required: true },
          ],
          submit_button: { id: "login-submit", text: "Log In" },
        },
        register_link: { text: "Don't have an account? Register", href: "/register" },
      },
    };
  }

  // Register
  if (route === "/register") {
    return {
      page: "register",
      title: "Create Account",
      elements: {
        form: {
          id: "register-form",
          fields: [
            { name: "name", type: "text", label: "Full Name", required: true },
            { name: "email", type: "email", label: "Email", required: true },
            { name: "password", type: "password", label: "Password", required: true, minLength: 6 },
            { name: "confirm_password", type: "password", label: "Confirm Password", required: true },
          ],
          submit_button: { id: "register-submit", text: "Create Account" },
        },
      },
    };
  }

  // Products listing
  if (route === "/products") {
    const products = db.prepare("SELECT id, name, price, category, stock, image_url FROM products ORDER BY id").all();
    const categories = db.prepare("SELECT DISTINCT category FROM products").all().map(r => r.category);
    return {
      page: "products",
      title: "All Products",
      elements: {
        search_bar: { id: "search-input", placeholder: "Search products..." },
        category_filter: { id: "category-filter", options: ["All", ...categories] },
        sort_select: { id: "sort-select", options: ["Default", "Price: Low to High", "Price: High to Low"] },
        product_grid: products.map(p => ({
          id: `product-${p.id}`,
          product_id: p.id,
          name: p.name,
          price: p.price,
          category: p.category,
          stock: p.stock,
          add_to_cart_button: { id: `add-to-cart-${p.id}`, text: "Add to Cart" },
          view_detail_link: { href: `/products/${p.id}`, text: "View Details" },
        })),
      },
    };
  }

  // Product detail
  const productMatch = route.match(/^\/products\/(\d+)$/);
  if (productMatch) {
    const product = db.prepare("SELECT * FROM products WHERE id = ?").get(productMatch[1]);
    if (!product) throw new Error("Product not found");

    const reviews = db.prepare(
      "SELECT r.*, u.name as user_name FROM reviews r JOIN users u ON r.user_id = u.id WHERE r.product_id = ? ORDER BY r.created_at DESC"
    ).all(product.id);
    const avgRating = reviews.length > 0 ? reviews.reduce((s, r) => s + r.rating, 0) / reviews.length : null;

    return {
      page: "product_detail",
      title: product.name,
      elements: {
        product: {
          id: product.id,
          name: product.name,
          description: product.description,
          price: product.price,
          stock: product.stock,
          category: product.category,
          image_url: product.image_url,
        },
        add_to_cart_button: { id: `add-to-cart-${product.id}`, text: "Add to Cart", disabled: product.stock === 0 },
        add_to_wishlist_button: { id: `add-to-wishlist-${product.id}`, text: "Add to Wishlist" },
        reviews_section: {
          avg_rating: avgRating,
          count: reviews.length,
          reviews: reviews.map(r => ({
            id: `review-${r.id}`,
            user_name: r.user_name,
            rating: r.rating,
            comment: r.comment,
            created_at: r.created_at,
          })),
        },
        review_form: userId ? {
          id: "review-form",
          fields: [
            { name: "rating", type: "number", label: "Rating (1-5)", min: 1, max: 5, required: true },
            { name: "comment", type: "textarea", label: "Comment" },
          ],
          submit_button: { id: "submit-review", text: "Submit Review" },
        } : null,
      },
    };
  }

  // Cart
  if (route === "/cart") {
    if (!userId) return { page: "cart", title: "Cart", elements: { message: "Please log in to view your cart" } };

    const items = db.prepare(
      "SELECT ci.id, ci.product_id, ci.quantity, p.name, p.price, p.stock FROM cart_items ci JOIN products p ON ci.product_id = p.id WHERE ci.user_id = ?"
    ).all(userId);

    const cartItems = items.map(i => ({
      id: `cart-item-${i.id}`,
      cart_item_id: i.id,
      product_id: i.product_id,
      name: i.name,
      price: i.price,
      quantity: i.quantity,
      subtotal: +(i.price * i.quantity).toFixed(2),
      quantity_input: { id: `qty-${i.id}`, value: i.quantity, max: i.stock },
      remove_button: { id: `remove-${i.id}`, text: "Remove" },
    }));
    const total = +cartItems.reduce((s, i) => s + i.subtotal, 0).toFixed(2);

    return {
      page: "cart",
      title: "Shopping Cart",
      elements: {
        cart_items: cartItems,
        count: cartItems.length,
        grand_total: total,
        clear_cart_button: { id: "clear-cart", text: "Clear Cart" },
        checkout_button: { id: "checkout-btn", text: "Proceed to Checkout", href: "/checkout", disabled: cartItems.length === 0 },
      },
    };
  }

  // Checkout
  if (route === "/checkout") {
    if (!userId) return { page: "checkout", title: "Checkout", elements: { message: "Please log in" } };

    const items = db.prepare(
      "SELECT ci.quantity, p.name, p.price FROM cart_items ci JOIN products p ON ci.product_id = p.id WHERE ci.user_id = ?"
    ).all(userId);
    const subtotal = +items.reduce((s, i) => s + i.price * i.quantity, 0).toFixed(2);

    const user = db.prepare("SELECT name, address FROM users WHERE id = ?").get(userId);

    return {
      page: "checkout",
      title: "Checkout",
      elements: {
        order_summary: {
          items: items.map(i => ({ name: i.name, quantity: i.quantity, price: i.price, subtotal: +(i.price * i.quantity).toFixed(2) })),
          subtotal,
        },
        shipping_form: {
          id: "shipping-form",
          fields: [
            { name: "shipping_name", type: "text", label: "Full Name", value: user?.name || "", required: true },
            { name: "shipping_address", type: "text", label: "Address", value: user?.address || "", required: true },
            { name: "shipping_city", type: "text", label: "City", required: true },
            { name: "shipping_zip", type: "text", label: "ZIP Code", required: true },
          ],
        },
        coupon_input: { id: "coupon-code", placeholder: "Enter coupon code" },
        apply_coupon_button: { id: "apply-coupon", text: "Apply Coupon" },
        place_order_button: { id: "place-order", text: "Place Order" },
      },
    };
  }

  // Order History
  if (route === "/orders") {
    if (!userId) return { page: "orders", title: "Orders", elements: { message: "Please log in" } };

    const orders = db.prepare("SELECT id, total, status, created_at, coupon_code, discount FROM orders WHERE user_id = ? ORDER BY created_at DESC").all(userId);
    return {
      page: "order_history",
      title: "Order History",
      elements: {
        orders: orders.map(o => ({
          id: `order-${o.id}`,
          order_id: o.id,
          total: o.total,
          status: o.status,
          created_at: o.created_at,
          coupon_code: o.coupon_code,
          discount: o.discount,
          view_link: { href: `/orders/${o.id}`, text: "View Details" },
        })),
        count: orders.length,
      },
    };
  }

  // Order Detail
  const orderMatch = route.match(/^\/orders\/(\d+)$/);
  if (orderMatch) {
    if (!userId) return { page: "order_detail", title: "Order", elements: { message: "Please log in" } };

    const order = db.prepare("SELECT * FROM orders WHERE id = ? AND user_id = ?").get(orderMatch[1], userId);
    if (!order) throw new Error("Order not found");

    const items = db.prepare("SELECT * FROM order_items WHERE order_id = ?").all(order.id);

    return {
      page: "order_detail",
      title: `Order #${order.id}`,
      elements: {
        order: {
          id: order.id,
          total: order.total,
          status: order.status,
          shipping_name: order.shipping_name,
          shipping_address: order.shipping_address,
          shipping_city: order.shipping_city,
          shipping_zip: order.shipping_zip,
          coupon_code: order.coupon_code,
          discount: order.discount,
          created_at: order.created_at,
        },
        items: items.map(i => ({
          product_id: i.product_id,
          name: i.product_name,
          quantity: i.quantity,
          price: i.price,
          subtotal: +(i.price * i.quantity).toFixed(2),
        })),
        cancel_button: order.status === "pending" ? { id: "cancel-order", text: "Cancel Order" } : null,
      },
    };
  }

  // Profile
  if (route === "/profile") {
    if (!userId) return { page: "profile", title: "Profile", elements: { message: "Please log in" } };

    const user = db.prepare("SELECT id, name, email, address, created_at FROM users WHERE id = ?").get(userId);
    return {
      page: "profile",
      title: "My Profile",
      elements: {
        profile_form: {
          id: "profile-form",
          fields: [
            { name: "name", type: "text", label: "Name", value: user.name },
            { name: "email", type: "email", label: "Email", value: user.email },
            { name: "address", type: "text", label: "Address", value: user.address },
          ],
          submit_button: { id: "update-profile", text: "Save Changes" },
        },
        password_form: {
          id: "password-form",
          fields: [
            { name: "current_password", type: "password", label: "Current Password", required: true },
            { name: "new_password", type: "password", label: "New Password", required: true, minLength: 6 },
          ],
          submit_button: { id: "change-password", text: "Change Password" },
        },
      },
    };
  }

  // Wishlist
  if (route === "/wishlist") {
    if (!userId) return { page: "wishlist", title: "Wishlist", elements: { message: "Please log in" } };

    const items = db.prepare(
      "SELECT w.id, w.product_id, p.name, p.price, p.stock, p.category FROM wishlist_items w JOIN products p ON w.product_id = p.id WHERE w.user_id = ?"
    ).all(userId);

    return {
      page: "wishlist",
      title: "My Wishlist",
      elements: {
        items: items.map(i => ({
          id: `wishlist-${i.id}`,
          wishlist_item_id: i.id,
          product_id: i.product_id,
          name: i.name,
          price: i.price,
          stock: i.stock,
          category: i.category,
          move_to_cart_button: { id: `move-to-cart-${i.id}`, text: "Move to Cart", disabled: i.stock === 0 },
          remove_button: { id: `remove-wishlist-${i.id}`, text: "Remove" },
        })),
        count: items.length,
      },
    };
  }

  // Contact
  if (route === "/contact") {
    return {
      page: "contact",
      title: "Contact Us",
      elements: {
        form: {
          id: "contact-form",
          fields: [
            { name: "name", type: "text", label: "Your Name", required: true },
            { name: "email", type: "email", label: "Your Email", required: true },
            { name: "subject", type: "text", label: "Subject", required: true },
            { name: "message", type: "textarea", label: "Message", required: true },
          ],
          submit_button: { id: "send-message", text: "Send Message" },
        },
      },
    };
  }

  throw new Error(`Unknown route: ${route}`);
}

// ── Health check ──
app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "browser-gym-webapp" });
});

// ── Serve React SPA (static files) ──
app.use(express.static(path.join(__dirname, "dist")));
app.get("*", (_req, res) => {
  const indexPath = path.join(__dirname, "dist", "index.html");
  const fs = require("fs");
  if (fs.existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.json({ message: "Browser Gym API is running. React SPA not built yet." });
  }
});

app.listen(PORT, () => {
  console.log(`Browser Gym webapp running on port ${PORT}`);
});
