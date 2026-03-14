/**
 * SQLite schema + seed data for Browser Gym.
 *
 * Tables: users, products, reviews, cart_items, wishlist_items,
 *         orders, order_items, coupons, contacts
 *
 * Session isolation: each X-Session-ID gets its own .db file.
 * The default (no header) uses data/app.db.
 */

const Database = require("better-sqlite3");
const path = require("path");
const fs = require("fs");
const bcrypt = require("bcryptjs");

const DATA_DIR = path.join(__dirname, "..", "data");
const SESSIONS_DIR = path.join(DATA_DIR, "sessions");
const DEFAULT_DB = path.join(DATA_DIR, "app.db");

// Ensure directories exist
fs.mkdirSync(SESSIONS_DIR, { recursive: true });

/** Get DB path for a session (or default). */
function getDbPath(sessionId) {
  if (sessionId) {
    return path.join(SESSIONS_DIR, `${sessionId}.db`);
  }
  return DEFAULT_DB;
}

/** Open (or create) a database connection. */
function openDb(sessionId) {
  const dbPath = getDbPath(sessionId);
  const db = new Database(dbPath);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  return db;
}

/** Create all tables. */
function createTables(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      address TEXT DEFAULT '',
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      description TEXT DEFAULT '',
      price REAL NOT NULL,
      image_url TEXT DEFAULT '',
      stock INTEGER NOT NULL DEFAULT 0,
      category TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS reviews (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      product_id INTEGER NOT NULL REFERENCES products(id),
      user_id INTEGER NOT NULL REFERENCES users(id),
      rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
      comment TEXT DEFAULT '',
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS cart_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      product_id INTEGER NOT NULL REFERENCES products(id),
      quantity INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS wishlist_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      product_id INTEGER NOT NULL REFERENCES products(id),
      added_at TEXT DEFAULT (datetime('now')),
      UNIQUE(user_id, product_id)
    );

    CREATE TABLE IF NOT EXISTS orders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      total REAL NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending',
      shipping_name TEXT DEFAULT '',
      shipping_address TEXT DEFAULT '',
      shipping_city TEXT DEFAULT '',
      shipping_zip TEXT DEFAULT '',
      coupon_code TEXT DEFAULT '',
      discount REAL DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS order_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id INTEGER NOT NULL REFERENCES orders(id),
      product_id INTEGER NOT NULL,
      product_name TEXT NOT NULL,
      quantity INTEGER NOT NULL,
      price REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS coupons (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      code TEXT UNIQUE NOT NULL,
      discount_percent REAL NOT NULL,
      min_order REAL NOT NULL DEFAULT 0,
      active INTEGER NOT NULL DEFAULT 1,
      uses_remaining INTEGER NOT NULL DEFAULT -1
    );

    CREATE TABLE IF NOT EXISTS contacts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL,
      subject TEXT NOT NULL,
      message TEXT NOT NULL,
      created_at TEXT DEFAULT (datetime('now'))
    );
  `);
}

/** Seed products, coupons, and test users. */
function seedData(db) {
  // Skip if already seeded
  const count = db.prepare("SELECT COUNT(*) as c FROM products").get();
  if (count.c > 0) return;

  const insertProduct = db.prepare(
    "INSERT INTO products (name, description, price, image_url, stock, category) VALUES (?, ?, ?, ?, ?, ?)"
  );

  const products = [
    // Electronics (4)
    ["Wireless Headphones", "Bluetooth over-ear headphones with noise cancellation", 79.99, "/img/headphones.jpg", 25, "Electronics"],
    ["USB-C Hub", "7-in-1 USB-C hub with HDMI, USB 3.0, SD card reader", 34.99, "/img/usbhub.jpg", 50, "Electronics"],
    ["Mechanical Keyboard", "RGB mechanical keyboard with Cherry MX switches", 129.99, "/img/keyboard.jpg", 15, "Electronics"],
    ["Portable Charger", "20000mAh power bank with fast charging", 44.99, "/img/charger.jpg", 40, "Electronics"],
    // Clothing (4)
    ["Cotton T-Shirt", "Unisex cotton crew neck t-shirt, available in multiple colors", 19.99, "/img/tshirt.jpg", 100, "Clothing"],
    ["Denim Jacket", "Classic denim jacket with button closure", 59.99, "/img/denim.jpg", 20, "Clothing"],
    ["Running Shoes", "Lightweight running shoes with cushioned sole", 89.99, "/img/shoes.jpg", 30, "Clothing"],
    ["Wool Beanie", "Warm knitted wool beanie for winter", 14.99, "/img/beanie.jpg", 60, "Clothing"],
    // Books (4)
    ["JavaScript: The Good Parts", "A deep dive into the best features of JavaScript", 29.99, "/img/jsbook.jpg", 35, "Books"],
    ["Clean Code", "A handbook of agile software craftsmanship by Robert C. Martin", 39.99, "/img/cleancode.jpg", 20, "Books"],
    ["Design Patterns", "Elements of reusable object-oriented software", 49.99, "/img/patterns.jpg", 10, "Books"],
    ["The Pragmatic Programmer", "Your journey to mastery, 20th anniversary edition", 42.99, "/img/pragmatic.jpg", 1, "Books"],
    // Home (3)
    ["Desk Lamp", "LED desk lamp with adjustable brightness and color temperature", 32.99, "/img/lamp.jpg", 45, "Home"],
    ["Coffee Mug Set", "Set of 4 ceramic coffee mugs, 12oz each", 24.99, "/img/mugs.jpg", 35, "Home"],
    ["Plant Pot", "Minimalist ceramic plant pot with drainage hole", 18.99, "/img/pot.jpg", 50, "Home"],
  ];

  const insertMany = db.transaction(() => {
    for (const p of products) {
      insertProduct.run(...p);
    }
  });
  insertMany();

  // Coupons
  const insertCoupon = db.prepare(
    "INSERT INTO coupons (code, discount_percent, min_order, active, uses_remaining) VALUES (?, ?, ?, ?, ?)"
  );
  insertCoupon.run("SAVE10", 10, 50, 1, -1);    // 10% off, min $50, unlimited
  insertCoupon.run("SAVE20", 20, 100, 1, 5);     // 20% off, min $100, 5 uses left
  insertCoupon.run("EXPIRED01", 15, 0, 0, 0);    // Expired/inactive

  // Pre-existing users for login scenarios
  const insertUser = db.prepare(
    "INSERT INTO users (name, email, password_hash, address) VALUES (?, ?, ?, ?)"
  );
  const hash1 = bcrypt.hashSync("password123", 10);
  const hash2 = bcrypt.hashSync("securepass", 10);
  insertUser.run("Alice Johnson", "alice@example.com", hash1, "123 Main St, Springfield");
  insertUser.run("Bob Smith", "bob@example.com", hash2, "456 Oak Ave, Shelbyville");
}

/** Initialize a database: create tables + seed. */
function initDb(sessionId) {
  const db = openDb(sessionId);
  createTables(db);
  seedData(db);
  db.close();
}

/** Create a new session DB by initializing a fresh copy. */
function createSession(sessionId) {
  initDb(sessionId);
  return getDbPath(sessionId);
}

/** Delete a session DB. */
function deleteSession(sessionId) {
  const dbPath = getDbPath(sessionId);
  if (fs.existsSync(dbPath)) {
    fs.unlinkSync(dbPath);
  }
}

// Initialize default DB on load
initDb(null);

module.exports = { openDb, getDbPath, initDb, createSession, deleteSession };
