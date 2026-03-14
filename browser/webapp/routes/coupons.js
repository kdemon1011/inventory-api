/**
 * Coupon validation route.
 */

const express = require("express");
const router = express.Router();

/** POST /api/coupons/validate — validate a coupon code */
router.post("/validate", (req, res) => {
  const { code } = req.body;
  if (!code) return res.status(400).json({ error: "code is required" });

  const coupon = req.db.prepare("SELECT * FROM coupons WHERE code = ?").get(code);
  if (!coupon) return res.status(404).json({ error: "Coupon not found" });

  const valid = coupon.active === 1 && (coupon.uses_remaining === -1 || coupon.uses_remaining > 0);
  res.json({
    code: coupon.code,
    valid,
    discount_percent: coupon.discount_percent,
    min_order: coupon.min_order,
    reason: !valid ? "Coupon is expired or has no uses remaining" : null,
  });
});

module.exports = router;
