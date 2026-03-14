/**
 * Product routes: list (with search/filter/sort/pagination), detail, reviews.
 */

const express = require("express");
const router = express.Router();

/** GET /api/products — list with ?q=, ?category=, ?sort=, ?page=, ?limit= */
router.get("/", (req, res) => {
  const db = req.db;
  const { q, category, sort, page = 1, limit = 12 } = req.query;

  let where = [];
  let params = [];

  if (q) {
    where.push("(name LIKE ? OR description LIKE ?)");
    params.push(`%${q}%`, `%${q}%`);
  }
  if (category) {
    where.push("category = ?");
    params.push(category);
  }

  const whereClause = where.length > 0 ? `WHERE ${where.join(" AND ")}` : "";

  let orderClause = "ORDER BY id ASC";
  if (sort === "price_asc") orderClause = "ORDER BY price ASC";
  else if (sort === "price_desc") orderClause = "ORDER BY price DESC";

  const offset = (parseInt(page) - 1) * parseInt(limit);

  const total = db.prepare(`SELECT COUNT(*) as c FROM products ${whereClause}`).get(...params).c;
  const products = db.prepare(
    `SELECT * FROM products ${whereClause} ${orderClause} LIMIT ? OFFSET ?`
  ).all(...params, parseInt(limit), offset);

  res.json({
    products,
    total,
    page: parseInt(page),
    limit: parseInt(limit),
    pages: Math.ceil(total / parseInt(limit)),
  });
});

/** GET /api/products/:id — single product with reviews */
router.get("/:id", (req, res) => {
  const db = req.db;
  const product = db.prepare("SELECT * FROM products WHERE id = ?").get(req.params.id);
  if (!product) {
    return res.status(404).json({ error: "Product not found" });
  }

  const reviews = db.prepare(
    `SELECT r.*, u.name as user_name
     FROM reviews r JOIN users u ON r.user_id = u.id
     WHERE r.product_id = ?
     ORDER BY r.created_at DESC`
  ).all(req.params.id);

  const avgRating = reviews.length > 0
    ? reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length
    : null;

  res.json({ ...product, reviews, avg_rating: avgRating });
});

/** POST /api/products/:id/reviews — add a review (requires auth) */
router.post("/:id/reviews", (req, res) => {
  if (!req.userId) {
    return res.status(401).json({ error: "Not authenticated" });
  }
  const { rating, comment } = req.body;
  if (!rating || rating < 1 || rating > 5) {
    return res.status(400).json({ error: "Rating must be between 1 and 5" });
  }

  const db = req.db;
  const product = db.prepare("SELECT id FROM products WHERE id = ?").get(req.params.id);
  if (!product) {
    return res.status(404).json({ error: "Product not found" });
  }

  const result = db.prepare(
    "INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?, ?, ?, ?)"
  ).run(req.params.id, req.userId, rating, comment || "");

  res.status(201).json({ id: result.lastInsertRowid, product_id: parseInt(req.params.id), rating, comment: comment || "" });
});

module.exports = router;
