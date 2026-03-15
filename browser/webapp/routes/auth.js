/**
 * Auth routes: register, login, get current user.
 * Token is a simple base64-encoded user ID (sufficient for a gym).
 */

const express = require("express");
const bcrypt = require("bcryptjs");
const router = express.Router();

/** POST /api/auth/register */
router.post("/register", (req, res) => {
  const { name, email, password } = req.body;
  if (!name || !email || !password) {
    return res.status(400).json({ error: "name, email, and password are required" });
  }
  if (password.length < 6) {
    return res.status(400).json({ error: "Password must be at least 6 characters" });
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return res.status(400).json({ error: "Invalid email format" });
  }

  const db = req.db;
  const existing = db.prepare("SELECT id FROM users WHERE email = ?").get(email);
  if (existing) {
    return res.status(409).json({ error: "Email already registered" });
  }

  const hash = bcrypt.hashSync(password, 10);
  const result = db.prepare(
    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)"
  ).run(name, email, hash);

  const token = Buffer.from(String(result.lastInsertRowid)).toString("base64");
  res.status(201).json({ id: result.lastInsertRowid, name, email, token });
});

/** POST /api/auth/login */
router.post("/login", (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ error: "email and password are required" });
  }

  const db = req.db;
  const user = db.prepare("SELECT * FROM users WHERE email = ?").get(email);
  if (!user || !bcrypt.compareSync(password, user.password_hash)) {
    return res.status(401).json({ error: "Invalid email or password" });
  }

  const token = Buffer.from(String(user.id)).toString("base64");
  res.json({ id: user.id, name: user.name, email: user.email, token });
});

/** GET /api/auth/me — requires auth token */
router.get("/me", (req, res) => {
  if (!req.userId) {
    return res.status(401).json({ error: "Not authenticated" });
  }
  const user = req.db.prepare("SELECT id, name, email, address, created_at FROM users WHERE id = ?").get(req.userId);
  if (!user) {
    return res.status(404).json({ error: "User not found" });
  }
  res.json(user);
});

module.exports = router;
