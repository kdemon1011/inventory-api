/**
 * Contact form route.
 */

const express = require("express");
const router = express.Router();

/** POST /api/contact — submit contact form (no auth required) */
router.post("/", (req, res) => {
  const { name, email, subject, message } = req.body;
  if (!name || !email || !subject || !message) {
    return res.status(400).json({ error: "name, email, subject, and message are required" });
  }

  const result = req.db.prepare(
    "INSERT INTO contacts (name, email, subject, message) VALUES (?, ?, ?, ?)"
  ).run(name, email, subject, message);

  res.status(201).json({ id: result.lastInsertRowid, submitted: true });
});

module.exports = router;
