/**
 * Profile routes: view, update, change password.
 */

const express = require("express");
const bcrypt = require("bcryptjs");
const router = express.Router();

router.use((req, res, next) => {
  if (!req.userId) return res.status(401).json({ error: "Not authenticated" });
  next();
});

/** GET /api/profile */
router.get("/", (req, res) => {
  const user = req.db.prepare(
    "SELECT id, name, email, address, created_at FROM users WHERE id = ?"
  ).get(req.userId);
  if (!user) return res.status(404).json({ error: "User not found" });
  res.json(user);
});

/** PUT /api/profile — update name, email, address */
router.put("/", (req, res) => {
  const { name, email, address } = req.body;
  const db = req.db;

  // Check email uniqueness if changed
  if (email) {
    const existing = db.prepare("SELECT id FROM users WHERE email = ? AND id != ?").get(email, req.userId);
    if (existing) return res.status(409).json({ error: "Email already taken" });
  }

  const current = db.prepare("SELECT * FROM users WHERE id = ?").get(req.userId);
  db.prepare("UPDATE users SET name = ?, email = ?, address = ? WHERE id = ?").run(
    name || current.name,
    email || current.email,
    address !== undefined ? address : current.address,
    req.userId
  );

  const updated = db.prepare("SELECT id, name, email, address, created_at FROM users WHERE id = ?").get(req.userId);
  res.json(updated);
});

/** PUT /api/profile/password — change password */
router.put("/password", (req, res) => {
  const { current_password, new_password } = req.body;
  if (!current_password || !new_password) {
    return res.status(400).json({ error: "current_password and new_password are required" });
  }
  if (new_password.length < 6) {
    return res.status(400).json({ error: "New password must be at least 6 characters" });
  }

  const db = req.db;
  const user = db.prepare("SELECT * FROM users WHERE id = ?").get(req.userId);
  if (!bcrypt.compareSync(current_password, user.password_hash)) {
    return res.status(401).json({ error: "Current password is incorrect" });
  }

  const hash = bcrypt.hashSync(new_password, 10);
  db.prepare("UPDATE users SET password_hash = ? WHERE id = ?").run(hash, req.userId);
  res.json({ updated: true });
});

module.exports = router;
