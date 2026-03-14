import React from "react";

/**
 * Minimal React SPA shell for Browser Gym.
 * The agent interacts via MCP tools → Express API, not this UI directly.
 * This exists so the Docker container serves a valid SPA at /.
 */
export default function App() {
  return (
    <div id="app">
      <nav id="navbar">
        <a href="/">Home</a>
        <a href="/products">Products</a>
        <a href="/cart">Cart</a>
        <a href="/orders">Orders</a>
        <a href="/wishlist">Wishlist</a>
        <a href="/profile">Profile</a>
        <a href="/contact">Contact</a>
        <a href="/login">Login</a>
      </nav>
      <main id="content">
        <h1>BrowserGym Shop</h1>
        <p>This is the Browser Gym e-commerce application.</p>
        <p>Agent interaction happens via MCP tools through the OpenEnv API.</p>
      </main>
    </div>
  );
}
