/**
 * Wishlist routes: list, add, remove, move-to-cart.
 */

const express = require("express");
const router = express.Router();

router.use((req, res, next) => {
  if (!req.userId) return res.status(401).json({ error: "Not authenticated" });
  next();
});

/** GET /api/wishlist */
router.get("/", (req, res) => {
  const items = req.db.prepare(
    `SELECT w.id, w.product_id, w.added_at, p.name, p.price, p.stock, p.image_url, p.category
     FROM wishlist_items w JOIN products p ON w.product_id = p.id
     WHERE w.user_id = ?
     ORDER BY w.added_at DESC`
  ).all(req.userId);
  res.json({ items, count: items.length });
});

/** POST /api/wishlist — { product_id } */
router.post("/", (req, res) => {
  const { product_id } = req.body;
  if (!product_id) return res.status(400).json({ error: "product_id is required" });

  const db = req.db;
  const product = db.prepare("SELECT id FROM products WHERE id = ?").get(product_id);
  if (!product) return res.status(404).json({ error: "Product not found" });

  try {
    const result = db.prepare(
      "INSERT INTO wishlist_items (user_id, product_id) VALUES (?, ?)"
    ).run(req.userId, product_id);
    res.status(201).json({ id: result.lastInsertRowid, product_id });
  } catch (e) {
    if (e.code === "SQLITE_CONSTRAINT_UNIQUE") {
      return res.status(409).json({ error: "Product already in wishlist" });
    }
    throw e;
  }
});

/** DELETE /api/wishlist/:id */
router.delete("/:id", (req, res) => {
  const result = req.db.prepare(
    "DELETE FROM wishlist_items WHERE id = ? AND user_id = ?"
  ).run(req.params.id, req.userId);
  if (result.changes === 0) return res.status(404).json({ error: "Wishlist item not found" });
  res.json({ deleted: true });
});

/** POST /api/wishlist/:id/move-to-cart */
router.post("/:id/move-to-cart", (req, res) => {
  const db = req.db;
  const wishItem = db.prepare(
    `SELECT w.*, p.stock FROM wishlist_items w JOIN products p ON w.product_id = p.id
     WHERE w.id = ? AND w.user_id = ?`
  ).get(req.params.id, req.userId);

  if (!wishItem) return res.status(404).json({ error: "Wishlist item not found" });
  if (wishItem.stock < 1) return res.status(400).json({ error: "Product is out of stock" });

  const moveToCart = db.transaction(() => {
    // Check if already in cart
    const existing = db.prepare(
      "SELECT * FROM cart_items WHERE user_id = ? AND product_id = ?"
    ).get(req.userId, wishItem.product_id);

    if (existing) {
      const newQty = existing.quantity + 1;
      if (newQty > wishItem.stock) {
        throw new Error(`Cannot exceed stock. Available: ${wishItem.stock}`);
      }
      db.prepare("UPDATE cart_items SET quantity = ? WHERE id = ?").run(newQty, existing.id);
    } else {
      db.prepare(
        "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, 1)"
      ).run(req.userId, wishItem.product_id);
    }

    // Remove from wishlist
    db.prepare("DELETE FROM wishlist_items WHERE id = ?").run(wishItem.id);
  });

  try {
    moveToCart();
    res.json({ moved: true, product_id: wishItem.product_id });
  } catch (e) {
    res.status(400).json({ error: e.message });
  }
});

module.exports = router;
