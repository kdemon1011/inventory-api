/**
 * Cart routes: get, add, update quantity, remove item, clear all.
 */

const express = require("express");
const router = express.Router();

/** Auth guard for all cart routes */
router.use((req, res, next) => {
  if (!req.userId) return res.status(401).json({ error: "Not authenticated" });
  next();
});

/** GET /api/cart */
router.get("/", (req, res) => {
  const db = req.db;
  const items = db.prepare(
    `SELECT ci.id, ci.product_id, ci.quantity, p.name, p.price, p.stock, p.image_url
     FROM cart_items ci JOIN products p ON ci.product_id = p.id
     WHERE ci.user_id = ?`
  ).all(req.userId);

  const subtotals = items.map((i) => ({ ...i, subtotal: +(i.price * i.quantity).toFixed(2) }));
  const total = +subtotals.reduce((s, i) => s + i.subtotal, 0).toFixed(2);

  res.json({ items: subtotals, count: items.length, total });
});

/** POST /api/cart — add item { product_id, quantity } */
router.post("/", (req, res) => {
  const { product_id, quantity = 1 } = req.body;
  if (!product_id) return res.status(400).json({ error: "product_id is required" });

  const db = req.db;
  const product = db.prepare("SELECT * FROM products WHERE id = ?").get(product_id);
  if (!product) return res.status(404).json({ error: "Product not found" });
  if (product.stock < quantity) {
    return res.status(400).json({ error: `Insufficient stock. Available: ${product.stock}` });
  }

  // If already in cart, increment quantity
  const existing = db.prepare(
    "SELECT * FROM cart_items WHERE user_id = ? AND product_id = ?"
  ).get(req.userId, product_id);

  if (existing) {
    const newQty = existing.quantity + quantity;
    if (newQty > product.stock) {
      return res.status(400).json({ error: `Cannot exceed stock. Available: ${product.stock}` });
    }
    db.prepare("UPDATE cart_items SET quantity = ? WHERE id = ?").run(newQty, existing.id);
    return res.json({ id: existing.id, product_id, quantity: newQty });
  }

  const result = db.prepare(
    "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)"
  ).run(req.userId, product_id, quantity);

  res.status(201).json({ id: result.lastInsertRowid, product_id, quantity });
});

/** PUT /api/cart/:id — update quantity */
router.put("/:id", (req, res) => {
  const { quantity } = req.body;
  if (!quantity || quantity < 1) return res.status(400).json({ error: "quantity must be >= 1" });

  const db = req.db;
  const item = db.prepare("SELECT ci.*, p.stock FROM cart_items ci JOIN products p ON ci.product_id = p.id WHERE ci.id = ? AND ci.user_id = ?").get(req.params.id, req.userId);
  if (!item) return res.status(404).json({ error: "Cart item not found" });
  if (quantity > item.stock) {
    return res.status(400).json({ error: `Cannot exceed stock. Available: ${item.stock}` });
  }

  db.prepare("UPDATE cart_items SET quantity = ? WHERE id = ?").run(quantity, req.params.id);
  res.json({ id: parseInt(req.params.id), quantity });
});

/** DELETE /api/cart/:id — remove one item */
router.delete("/:id", (req, res) => {
  const db = req.db;
  const result = db.prepare("DELETE FROM cart_items WHERE id = ? AND user_id = ?").run(req.params.id, req.userId);
  if (result.changes === 0) return res.status(404).json({ error: "Cart item not found" });
  res.json({ deleted: true });
});

/** DELETE /api/cart — clear entire cart */
router.delete("/", (req, res) => {
  req.db.prepare("DELETE FROM cart_items WHERE user_id = ?").run(req.userId);
  res.json({ cleared: true });
});

module.exports = router;
