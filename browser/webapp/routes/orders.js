/**
 * Order routes: checkout, list, detail, cancel.
 */

const express = require("express");
const router = express.Router();

router.use((req, res, next) => {
  if (!req.userId) return res.status(401).json({ error: "Not authenticated" });
  next();
});

/** POST /api/orders/checkout */
router.post("/checkout", (req, res) => {
  const { shipping_name, shipping_address, shipping_city, shipping_zip, coupon_code } = req.body;
  if (!shipping_name || !shipping_address || !shipping_city || !shipping_zip) {
    return res.status(400).json({ error: "All shipping fields are required (shipping_name, shipping_address, shipping_city, shipping_zip)" });
  }

  const db = req.db;

  // Get cart items
  const cartItems = db.prepare(
    `SELECT ci.*, p.name as product_name, p.price, p.stock
     FROM cart_items ci JOIN products p ON ci.product_id = p.id
     WHERE ci.user_id = ?`
  ).all(req.userId);

  if (cartItems.length === 0) {
    return res.status(400).json({ error: "Cart is empty" });
  }

  // Validate stock
  for (const item of cartItems) {
    if (item.quantity > item.stock) {
      return res.status(400).json({
        error: `Insufficient stock for "${item.product_name}". Available: ${item.stock}, Requested: ${item.quantity}`
      });
    }
  }

  // Calculate subtotal
  let subtotal = cartItems.reduce((s, i) => s + i.price * i.quantity, 0);

  // Apply coupon
  let discount = 0;
  let appliedCoupon = "";
  if (coupon_code) {
    const coupon = db.prepare("SELECT * FROM coupons WHERE code = ?").get(coupon_code);
    if (!coupon) {
      return res.status(400).json({ error: `Coupon "${coupon_code}" not found` });
    }
    if (!coupon.active) {
      return res.status(400).json({ error: `Coupon "${coupon_code}" is expired or inactive` });
    }
    if (coupon.uses_remaining === 0) {
      return res.status(400).json({ error: `Coupon "${coupon_code}" has no uses remaining` });
    }
    if (subtotal < coupon.min_order) {
      return res.status(400).json({
        error: `Order subtotal $${subtotal.toFixed(2)} does not meet minimum $${coupon.min_order.toFixed(2)} for coupon "${coupon_code}"`
      });
    }
    discount = +(subtotal * coupon.discount_percent / 100).toFixed(2);
    appliedCoupon = coupon_code;

    // Decrement uses if limited
    if (coupon.uses_remaining > 0) {
      db.prepare("UPDATE coupons SET uses_remaining = uses_remaining - 1 WHERE id = ?").run(coupon.id);
    }
  }

  const total = +(subtotal - discount).toFixed(2);

  // Create order in a transaction
  const placeOrder = db.transaction(() => {
    const orderResult = db.prepare(
      `INSERT INTO orders (user_id, total, status, shipping_name, shipping_address, shipping_city, shipping_zip, coupon_code, discount)
       VALUES (?, ?, 'pending', ?, ?, ?, ?, ?, ?)`
    ).run(req.userId, total, shipping_name, shipping_address, shipping_city, shipping_zip, appliedCoupon, discount);

    const orderId = orderResult.lastInsertRowid;

    const insertItem = db.prepare(
      "INSERT INTO order_items (order_id, product_id, product_name, quantity, price) VALUES (?, ?, ?, ?, ?)"
    );
    const updateStock = db.prepare(
      "UPDATE products SET stock = stock - ? WHERE id = ?"
    );

    for (const item of cartItems) {
      insertItem.run(orderId, item.product_id, item.product_name, item.quantity, item.price);
      updateStock.run(item.quantity, item.product_id);
    }

    // Clear cart
    db.prepare("DELETE FROM cart_items WHERE user_id = ?").run(req.userId);

    return orderId;
  });

  const orderId = placeOrder();

  res.status(201).json({
    order_id: orderId,
    total,
    discount,
    coupon_code: appliedCoupon,
    items: cartItems.length,
    status: "pending",
  });
});

/** GET /api/orders */
router.get("/", (req, res) => {
  const orders = req.db.prepare(
    "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC"
  ).all(req.userId);
  res.json({ orders });
});

/** GET /api/orders/:id */
router.get("/:id", (req, res) => {
  const db = req.db;
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND user_id = ?").get(req.params.id, req.userId);
  if (!order) return res.status(404).json({ error: "Order not found" });

  const items = db.prepare("SELECT * FROM order_items WHERE order_id = ?").all(order.id);
  res.json({ ...order, items });
});

/** PUT /api/orders/:id/cancel */
router.put("/:id/cancel", (req, res) => {
  const db = req.db;
  const order = db.prepare("SELECT * FROM orders WHERE id = ? AND user_id = ?").get(req.params.id, req.userId);
  if (!order) return res.status(404).json({ error: "Order not found" });
  if (order.status !== "pending") {
    return res.status(400).json({ error: `Cannot cancel order with status "${order.status}". Only pending orders can be cancelled.` });
  }

  // Restore stock
  const items = db.prepare("SELECT * FROM order_items WHERE order_id = ?").all(order.id);
  const restoreAndCancel = db.transaction(() => {
    for (const item of items) {
      db.prepare("UPDATE products SET stock = stock + ? WHERE id = ?").run(item.quantity, item.product_id);
    }
    db.prepare("UPDATE orders SET status = 'cancelled' WHERE id = ?").run(order.id);
  });
  restoreAndCancel();

  res.json({ id: order.id, status: "cancelled" });
});

module.exports = router;
