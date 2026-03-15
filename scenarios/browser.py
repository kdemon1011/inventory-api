"""
Scenario definitions for the Browser Gym.

ALL scenarios are COMPLEX — designed to challenge and break SOTA models through:
  - Multi-step chains (15-30+ tool calls)
  - Cross-page state verification
  - Precise numerical verification (rounding, discounts)
  - Error recovery (coupon failures, stock limits)
  - Authentication state management (multi-user sessions)
  - False premises embedded in prompts (model must verify, not trust)
  - Semantic traps (move-to-cart vs. add-to-cart, different side effects)

Each scenario uses unique emails (sc{N}@browser.test) to prevent cross-scenario conflicts
when run in parallel via concurrent sessions.

Seed data reference:
  Products (15): Electronics 4, Clothing 4, Books 4, Home 3
  Coupons: SAVE10 (10%, min $50), SAVE20 (20%, min $100), EXPIRED01 (inactive)
  Users: Alice (alice@example.com / password123), Bob (bob@example.com / securepass)
"""

from rewards.base import Scenario


BROWSER_SCENARIOS = [
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. Coupon Threshold Trap
    #    Model must: search 4 categories, identify cheapest per category,
    #    add all 4, attempt SAVE20 (fails — $98.96 < $100), recover by
    #    adding a 5th item, re-apply SAVE20, checkout.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Scenario(
        id="coupon_threshold_trap",
        prompt=(
            "Register a new account with name 'Threshold Tester', email 'sc1@browser.test', "
            "password 'Sc1Pass!'. Your task: build a cart containing exactly the CHEAPEST "
            "product from each of the four categories (Electronics, Clothing, Books, Home). "
            "Search each category to identify the cheapest item — do not guess.\n\n"
            "After adding all four cheapest items, apply the SAVE20 coupon code at checkout. "
            "SAVE20 offers 20% off but requires a minimum order of $100. If the coupon is "
            "rejected, determine exactly how much your subtotal falls short, add a Cotton T-Shirt "
            "(product ID 5, $19.99) to push the total over the threshold, and then checkout "
            "with SAVE20 applied.\n\n"
            "Shipping: name='Threshold Tester', address='100 Coupon Lane', city='Discount City', "
            "zip='10020'.\n\n"
            "Expected outcome: 5 items in the order, SAVE20 coupon applied, discount is exactly "
            "20% of the pre-discount subtotal."
        ),
        expected_tools=[
            "navigate", "fill_form", "submit_form", "search_products",
            "add_to_cart", "checkout",
        ],
        max_steps=25,
        outcome_checks=[
            {"type": "user_exists", "email": "sc1@browser.test"},
            {"type": "order_exists", "email": "sc1@browser.test"},
            {"type": "order_coupon", "email": "sc1@browser.test", "order_index": 0, "value": "SAVE20"},
            # USB-C Hub $34.99 + Wool Beanie $14.99 + JS Good Parts $29.99 + Plant Pot $18.99 + T-Shirt $19.99 = $118.95
            # SAVE20: 20% of $118.95 = $23.79
            {"type": "order_discount", "email": "sc1@browser.test", "order_index": 0, "value": 23.79},
            {"type": "order_total", "email": "sc1@browser.test", "order_index": 0, "value": 95.16},
            {"type": "order_item_count", "email": "sc1@browser.test", "order_index": 0, "expected": 5},
        ],
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. Stock Deplete → Cancel → Verify Restore → Reorder
    #    Tests stock lifecycle: buy last copy, cancel (stock restores),
    #    re-buy. Model must verify intermediate stock state.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Scenario(
        id="stock_deplete_cancel_reorder",
        prompt=(
            "Login as Bob (email: bob@example.com, password: securepass).\n\n"
            "The book 'The Pragmatic Programmer' (product ID 12) has only 1 copy left in stock. "
            "Add it to your cart (quantity 1) and checkout immediately with shipping: "
            "name='Bob Smith', address='456 Oak Ave', city='Shelbyville', zip='62565'.\n\n"
            "After the order is placed, navigate to the order detail page and cancel the order. "
            "After cancellation, navigate to the product page for 'The Pragmatic Programmer' "
            "and verify the stock has been restored to 1.\n\n"
            "Now add the same book to your cart again (quantity 1) and place a SECOND order "
            "with the same shipping details. Do NOT cancel this order.\n\n"
            "At the end you should have exactly 2 orders: the first one cancelled, the second "
            "one pending. The product stock should be 0."
        ),
        expected_tools=[
            "navigate", "fill_form", "submit_form", "add_to_cart",
            "checkout", "click_element", "get_page_content", "assert_text_visible",
        ],
        max_steps=30,
        outcome_checks=[
            {"type": "order_count", "email": "bob@example.com", "expected": 2},
            {"type": "order_status", "email": "bob@example.com", "order_index": 0, "value": "pending"},
            {"type": "order_status", "email": "bob@example.com", "order_index": 1, "value": "cancelled"},
            {"type": "product_stock", "product_id": 12, "value": 0},
            {"type": "order_item_count", "email": "bob@example.com", "order_index": 0, "expected": 1},
        ],
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. False Price Claim + Optimal Coupon Selection
    #    Prompt embeds a WRONG price ($24.99 for cheapest book — actually
    #    $29.99). Model must search and verify, not trust the prompt.
    #    Then choose SAVE20 over SAVE10 via mental math.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Scenario(
        id="false_price_optimal_coupon",
        prompt=(
            "Login as Alice (email: alice@example.com, password: password123).\n\n"
            "Add these three products to your cart:\n"
            "  1. Mechanical Keyboard (product ID 3) — from Electronics, $129.99\n"
            "  2. Running Shoes (product ID 7) — from Clothing, $89.99\n"
            "  3. The cheapest book in the store — I believe it costs around $24.99\n\n"
            "IMPORTANT: Do NOT trust the price I gave for the cheapest book. Search the "
            "Books category and verify the actual cheapest book's name and price before adding it.\n\n"
            "After adding all three items, your cart will be over $100. You have two valid "
            "coupons available:\n"
            "  - SAVE10: 10% off (minimum order $50)\n"
            "  - SAVE20: 20% off (minimum order $100)\n\n"
            "Calculate which coupon saves you more money. Apply the BETTER coupon and checkout "
            "with shipping: name='Alice Johnson', address='123 Main St', city='Springfield', "
            "zip='62704'.\n\n"
            "The order total should reflect exactly 20% off the correct subtotal."
        ),
        expected_tools=[
            "navigate", "fill_form", "submit_form", "search_products",
            "add_to_cart", "checkout",
        ],
        max_steps=20,
        outcome_checks=[
            # Cheapest book is "JavaScript: The Good Parts" at $29.99 (NOT $24.99)
            # Subtotal: 129.99 + 89.99 + 29.99 = $249.97
            # SAVE20: 20% of $249.97 = $49.99 (49.994 rounds to 49.99)
            # Total: $249.97 - $49.99 = $199.98
            {"type": "order_exists", "email": "alice@example.com"},
            {"type": "order_coupon", "email": "alice@example.com", "order_index": 0, "value": "SAVE20"},
            {"type": "order_discount", "email": "alice@example.com", "order_index": 0, "value": 49.99},
            {"type": "order_total", "email": "alice@example.com", "order_index": 0, "value": 199.98},
            {"type": "order_item_count", "email": "alice@example.com", "order_index": 0, "expected": 3},
        ],
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. Cross-User Cart Isolation
    #    Register user A → add 2 items to cart → register user B
    #    (auth silently switches!) → verify B's cart is empty →
    #    checkout as B → login BACK as A → verify A's cart intact →
    #    checkout as A. Tests session state tracking.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Scenario(
        id="cross_user_cart_isolation",
        prompt=(
            "This scenario tests cart isolation between different users. Follow each step "
            "carefully — the authentication context changes implicitly.\n\n"
            "STEP 1: Register user A — name='User Alpha', email='sc4a@browser.test', "
            "password='Sc4PassA!'\n"
            "STEP 2: Add Wireless Headphones (product ID 1) and Desk Lamp (product ID 13) "
            "to User A's cart. DO NOT checkout yet.\n"
            "STEP 3: Register user B — name='User Beta', email='sc4b@browser.test', "
            "password='Sc4PassB!'\n"
            "⚠ IMPORTANT: After registering user B, you are now logged in as user B. "
            "User A's session is gone.\n"
            "STEP 4: Get user B's cart and verify it is EMPTY (0 items).\n"
            "STEP 5: Add Coffee Mug Set (product ID 14) to user B's cart and checkout "
            "with shipping: name='User Beta', address='200 Beta Blvd', city='BetaTown', "
            "zip='20002'.\n"
            "STEP 6: Now login as user A — navigate to login page, enter email 'sc4a@browser.test', "
            "password 'Sc4PassA!', submit the login form.\n"
            "STEP 7: Get user A's cart. It should STILL contain exactly 2 items "
            "(Wireless Headphones and Desk Lamp) — user B's checkout did not affect it.\n"
            "STEP 8: Checkout user A's cart with shipping: name='User Alpha', "
            "address='100 Alpha Ave', city='AlphaTown', zip='10001'."
        ),
        expected_tools=[
            "navigate", "fill_form", "submit_form", "add_to_cart",
            "get_cart", "checkout",
        ],
        max_steps=35,
        outcome_checks=[
            {"type": "user_exists", "email": "sc4a@browser.test"},
            {"type": "user_exists", "email": "sc4b@browser.test"},
            {"type": "order_exists", "email": "sc4b@browser.test"},
            {"type": "order_item_count", "email": "sc4b@browser.test", "order_index": 0, "expected": 1},
            {"type": "order_exists", "email": "sc4a@browser.test"},
            {"type": "order_item_count", "email": "sc4a@browser.test", "order_index": 0, "expected": 2},
            # Both carts should be empty after checkout
            {"type": "cart_count", "email": "sc4a@browser.test", "expected": 0},
            {"type": "cart_count", "email": "sc4b@browser.test", "expected": 0},
        ],
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5. Wishlist Move vs. Direct Add (Semantic Trap)
    #    "Move to cart" REMOVES from wishlist.
    #    "Add to cart" does NOT affect wishlist.
    #    Model must track both data structures correctly.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Scenario(
        id="wishlist_move_vs_direct_add",
        prompt=(
            "Register with name='Wishlist Tester', email='sc5@browser.test', "
            "password='Sc5Pass!'.\n\n"
            "PHASE 1 — Build wishlist:\n"
            "Add these 5 products to your wishlist (use toggle_wishlist):\n"
            "  - Wireless Headphones (ID 1, $79.99)\n"
            "  - Denim Jacket (ID 6, $59.99)\n"
            "  - Clean Code (ID 10, $39.99)\n"
            "  - Desk Lamp (ID 13, $32.99)\n"
            "  - Plant Pot (ID 15, $18.99)\n\n"
            "PHASE 2 — Move the two MOST EXPENSIVE items from wishlist to cart:\n"
            "Navigate to the wishlist page. Find the wishlist item IDs for 'Wireless Headphones' "
            "and 'Denim Jacket' (the two most expensive). Use click_element with "
            "'move-to-cart-{wishlist_item_id}' for each. This REMOVES them from the wishlist "
            "and adds them to the cart.\n\n"
            "PHASE 3 — Verify counts:\n"
            "The wishlist should now have exactly 3 items. The cart should have 2 items.\n\n"
            "PHASE 4 — Add a wishlist item to cart DIRECTLY:\n"
            "Use add_to_cart to add Clean Code (product ID 10) to the cart. This adds it "
            "to the cart but does NOT remove it from the wishlist. The wishlist should STILL "
            "have 3 items. The cart should now have 3 items.\n\n"
            "PHASE 5 — Checkout:\n"
            "Checkout with shipping: name='Wishlist Tester', address='555 Wish Way', "
            "city='WishCity', zip='55555'. No coupon.\n\n"
            "After checkout: cart=0 items, wishlist=3 items (Clean Code, Desk Lamp, Plant Pot), "
            "order has 3 line items, total = $79.99 + $59.99 + $39.99 = $179.97."
        ),
        expected_tools=[
            "navigate", "fill_form", "submit_form", "toggle_wishlist",
            "click_element", "add_to_cart", "get_cart", "checkout",
        ],
        max_steps=30,
        outcome_checks=[
            {"type": "user_exists", "email": "sc5@browser.test"},
            {"type": "order_exists", "email": "sc5@browser.test"},
            {"type": "order_total", "email": "sc5@browser.test", "order_index": 0, "value": 179.97},
            {"type": "order_item_count", "email": "sc5@browser.test", "order_index": 0, "expected": 3},
            # Wishlist should still have 3 items (move removed 2, direct add didn't affect wishlist)
            {"type": "wishlist_count", "email": "sc5@browser.test", "expected": 3},
            {"type": "cart_count", "email": "sc5@browser.test", "expected": 0},
        ],
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 6. Out-of-Stock Boundary + Error Recovery
    #    Try to buy 2 of a stock=1 item (fail), handle error,
    #    buy stock=10 at exact limit, verify stock depletion.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Scenario(
        id="out_of_stock_boundary",
        prompt=(
            "Register with name='Stock Tester', email='sc6@browser.test', "
            "password='Sc6Pass!'.\n\n"
            "TASK 1: Try to add 'The Pragmatic Programmer' (product ID 12, stock=1) "
            "to your cart with quantity 2. This MUST fail because only 1 copy is available. "
            "Observe the error message.\n\n"
            "TASK 2: Add the same book with quantity 1 (within stock). This should succeed.\n\n"
            "TASK 3: Add 'Design Patterns' (product ID 11, stock=10) to your cart with "
            "quantity 10 — exactly at the stock limit. This should succeed.\n\n"
            "TASK 4: Checkout with shipping: name='Stock Tester', address='777 Boundary Rd', "
            "city='EdgeCity', zip='77777'. No coupon.\n\n"
            "TASK 5: After checkout, attempt to add 'The Pragmatic Programmer' to the cart "
            "again (quantity 1). This should FAIL because the stock is now 0 after the "
            "previous purchase.\n\n"
            "Verify: Order has exactly 2 line items. Product ID 12 stock=0. Product ID 11 stock=0."
        ),
        expected_tools=[
            "navigate", "fill_form", "submit_form", "add_to_cart", "checkout",
        ],
        max_steps=20,
        outcome_checks=[
            {"type": "user_exists", "email": "sc6@browser.test"},
            {"type": "order_exists", "email": "sc6@browser.test"},
            {"type": "order_item_count", "email": "sc6@browser.test", "order_index": 0, "expected": 2},
            {"type": "product_stock", "product_id": 12, "value": 0},
            {"type": "product_stock", "product_id": 11, "value": 0},
            # Total: 42.99 + 499.90 = 542.89
            {"type": "order_total", "email": "sc6@browser.test", "order_index": 0, "value": 542.89},
        ],
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 7. Expired Coupon Cascade + Optimal Choice
    #    Try EXPIRED01 (fails), then choose between SAVE10 and SAVE20
    #    via arithmetic reasoning. Exact total verification.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Scenario(
        id="expired_coupon_cascade",
        prompt=(
            "Register with name='Coupon Tester', email='sc7@browser.test', "
            "password='Sc7Pass!'.\n\n"
            "Add these items to cart:\n"
            "  - Mechanical Keyboard (ID 3, $129.99) quantity 1\n"
            "  - Running Shoes (ID 7, $89.99) quantity 1\n"
            "  - Clean Code (ID 10, $39.99) quantity 1\n\n"
            "Subtotal: $259.97.\n\n"
            "Now attempt checkout with coupon code 'EXPIRED01'. This should FAIL because "
            "the coupon is expired/inactive. Note the error.\n\n"
            "You have two remaining coupon options:\n"
            "  - SAVE10: 10% off (minimum $50) → would save $26.00\n"
            "  - SAVE20: 20% off (minimum $100) → would save $51.99\n\n"
            "Choose the coupon that saves the MOST money. Checkout with it.\n"
            "Shipping: name='Coupon Tester', address='999 Cascade Blvd', city='CouponCity', "
            "zip='99999'.\n\n"
            "Verify: the order total should be exactly $207.98 with $51.99 discount."
        ),
        expected_tools=[
            "navigate", "fill_form", "submit_form", "add_to_cart", "checkout",
        ],
        max_steps=20,
        outcome_checks=[
            {"type": "user_exists", "email": "sc7@browser.test"},
            {"type": "order_exists", "email": "sc7@browser.test"},
            # SAVE20 is optimal: 20% of $259.97 = $51.99 (51.994 rounds to 51.99)
            {"type": "order_coupon", "email": "sc7@browser.test", "order_index": 0, "value": "SAVE20"},
            {"type": "order_discount", "email": "sc7@browser.test", "order_index": 0, "value": 51.99},
            {"type": "order_total", "email": "sc7@browser.test", "order_index": 0, "value": 207.98},
            {"type": "order_item_count", "email": "sc7@browser.test", "order_index": 0, "expected": 3},
        ],
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 8. Review + Cross-Page Verification
    #    Leave reviews on 2 different products, navigate between them,
    #    verify each review appears. Then buy both products.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Scenario(
        id="review_cross_page_verify",
        prompt=(
            "Login as Alice (email: alice@example.com, password: password123).\n\n"
            "TASK 1: Navigate to product 'Wireless Headphones' (product ID 1). "
            "Leave a 4-star review with comment 'Excellent noise cancellation, comfortable fit'. "
            "Fill the form fields 'rating' (value: '4') and 'comment' "
            "(value: 'Excellent noise cancellation, comfortable fit'), then submit the "
            "review form (form ID: review-form).\n\n"
            "TASK 2: Navigate to product 'USB-C Hub' (product ID 2). "
            "Leave a 2-star review with comment 'Ports stopped working after two weeks'. "
            "Same process: fill rating='2', comment='Ports stopped working after two weeks', "
            "submit review-form.\n\n"
            "TASK 3: Navigate BACK to 'Wireless Headphones' (product ID 1) and verify "
            "that your 4-star review text is visible on the page using assert_text_visible "
            "with the text 'Excellent noise cancellation'.\n\n"
            "TASK 4: Navigate BACK to 'USB-C Hub' (product ID 2) and verify your 2-star "
            "review is visible using assert_text_visible with 'Ports stopped working'.\n\n"
            "TASK 5: Add both products to cart (Wireless Headphones ID 1 and USB-C Hub ID 2) "
            "and checkout with shipping: name='Alice Johnson', address='123 Main St', "
            "city='Springfield', zip='62704'. No coupon."
        ),
        expected_tools=[
            "navigate", "fill_form", "submit_form", "assert_text_visible",
            "add_to_cart", "checkout",
        ],
        max_steps=25,
        outcome_checks=[
            {"type": "review_exists", "email": "alice@example.com", "product_id": 1},
            {"type": "review_rating", "email": "alice@example.com", "product_id": 1, "value": 4},
            {"type": "review_exists", "email": "alice@example.com", "product_id": 2},
            {"type": "review_rating", "email": "alice@example.com", "product_id": 2, "value": 2},
            {"type": "order_exists", "email": "alice@example.com"},
            # Total: 79.99 + 34.99 = $114.98
            {"type": "order_total", "email": "alice@example.com", "order_index": 0, "value": 114.98},
            {"type": "order_item_count", "email": "alice@example.com", "order_index": 0, "expected": 2},
        ],
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 9. Profile Update Mid-Flow + Shipping Verification
    #    Login, add items, update profile address, checkout with
    #    the NEW address. Verifies model doesn't use stale data.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Scenario(
        id="profile_update_checkout_verify",
        prompt=(
            "Login as Alice (email: alice@example.com, password: password123). "
            "Alice's current address is '123 Main St, Springfield'.\n\n"
            "STEP 1: Add Portable Charger (product ID 4, $44.99) and Denim Jacket "
            "(product ID 6, $59.99) to your cart. Subtotal: $104.98.\n\n"
            "STEP 2: Navigate to the profile page. Update Alice's address to "
            "'789 Elm St, Capital City, ST 54321'. Fill the 'address' field with "
            "this value and submit the profile form (form ID: profile-form).\n\n"
            "STEP 3: Navigate to verify the profile was updated — the address field "
            "should now show the new value.\n\n"
            "STEP 4: Checkout the cart. Use the UPDATED address for shipping:\n"
            "  shipping_name='Alice Johnson'\n"
            "  shipping_address='789 Elm St'\n"
            "  shipping_city='Capital City'\n"
            "  shipping_zip='54321'\n"
            "Apply SAVE10 coupon (10% off $104.98 = $10.50 discount, total = $94.48).\n\n"
            "Verify: order shipping address matches the new address, discount is correct, "
            "and the profile address was actually updated."
        ),
        expected_tools=[
            "navigate", "fill_form", "submit_form", "add_to_cart", "checkout",
        ],
        max_steps=20,
        outcome_checks=[
            {"type": "order_exists", "email": "alice@example.com"},
            {"type": "order_total", "email": "alice@example.com", "order_index": 0, "value": 94.48},
            {"type": "order_discount", "email": "alice@example.com", "order_index": 0, "value": 10.50},
            {"type": "order_coupon", "email": "alice@example.com", "order_index": 0, "value": "SAVE10"},
            {"type": "order_shipping", "email": "alice@example.com", "order_index": 0,
             "field": "shipping_address", "value": "789 Elm St"},
            {"type": "order_shipping", "email": "alice@example.com", "order_index": 0,
             "field": "shipping_city", "value": "Capital City"},
            {"type": "user_field", "email": "alice@example.com", "field": "address",
             "value": "789 Elm St, Capital City, ST 54321"},
        ],
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 10. Anonymous Contact → Register Same Email → Divergent Names
    #     Submit contact form while NOT logged in, then register with
    #     the same email but a DIFFERENT name. Verifies model doesn't
    #     confuse the two entities.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Scenario(
        id="contact_then_register_same_email",
        prompt=(
            "PHASE 1 — Anonymous contact (NOT logged in):\n"
            "Navigate to the contact page. Fill the contact form with:\n"
            "  name='Site Visitor'\n"
            "  email='sc10@browser.test'\n"
            "  subject='International Shipping'\n"
            "  message='Do you ship to Canada? What are the rates?'\n"
            "Submit the contact form (form ID: contact-form). Verify it was submitted.\n\n"
            "PHASE 2 — Registration with SAME email:\n"
            "Now register a new account: name='Sarah Chen', email='sc10@browser.test', "
            "password='Sc10Pass!'. Note: the name is 'Sarah Chen', NOT 'Site Visitor'. "
            "These are different entities — the contact form does not create an account.\n\n"
            "PHASE 3 — Shopping:\n"
            "Add Coffee Mug Set (product ID 14, $24.99) and Desk Lamp (product ID 13, $32.99) "
            "to cart. Checkout with shipping: name='Sarah Chen', address='42 Chen Way', "
            "city='ChenTown', zip='42042'. No coupon.\n\n"
            "Verify: contact form exists with email sc10@browser.test and name 'Site Visitor'. "
            "User account exists with email sc10@browser.test and name 'Sarah Chen'. "
            "Order exists with total $57.98."
        ),
        expected_tools=[
            "navigate", "fill_form", "submit_form", "add_to_cart", "checkout",
        ],
        max_steps=20,
        outcome_checks=[
            {"type": "contact_exists", "email": "sc10@browser.test"},
            {"type": "user_exists", "email": "sc10@browser.test"},
            {"type": "user_field", "email": "sc10@browser.test", "field": "name", "value": "Sarah Chen"},
            {"type": "order_exists", "email": "sc10@browser.test"},
            {"type": "order_total", "email": "sc10@browser.test", "order_index": 0, "value": 57.98},
            {"type": "order_item_count", "email": "sc10@browser.test", "order_index": 0, "expected": 2},
        ],
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 11. Bulk Cart Operations + Running Total Verification
    #     Add 5 items, update 3 quantities, remove 2 items, verify
    #     exact total, apply coupon, checkout. Tests precise cart
    #     manipulation and arithmetic across many operations.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Scenario(
        id="bulk_cart_ops_total_tracking",
        prompt=(
            "Login as Bob (email: bob@example.com, password: securepass).\n\n"
            "STEP 1 — Add 5 products to cart (quantity 1 each):\n"
            "  a) Wireless Headphones (ID 1, $79.99)\n"
            "  b) Mechanical Keyboard (ID 3, $129.99)\n"
            "  c) Cotton T-Shirt (ID 5, $19.99)\n"
            "  d) Running Shoes (ID 7, $89.99)\n"
            "  e) Desk Lamp (ID 13, $32.99)\n"
            "Verify cart has exactly 5 items.\n\n"
            "STEP 2 — Update quantities:\n"
            "  - Wireless Headphones → quantity 3\n"
            "  - Cotton T-Shirt → quantity 4\n"
            "  Leave all others at quantity 1.\n"
            "⚠ Use the cart_item_id from get_cart results, NOT the product_id.\n\n"
            "STEP 3 — Remove 2 items from cart:\n"
            "  - Remove Running Shoes\n"
            "  - Remove Desk Lamp\n"
            "Again, use cart_item_ids. Verify cart now has exactly 3 items.\n\n"
            "STEP 4 — Verify total:\n"
            "Get the cart. The total should be:\n"
            "  Headphones: $79.99 × 3 = $239.97\n"
            "  Keyboard:   $129.99 × 1 = $129.99\n"
            "  T-Shirt:    $19.99 × 4 = $79.96\n"
            "  Grand total: $449.92\n\n"
            "STEP 5 — Checkout with SAVE20 coupon (20% off $449.92 = $89.98, "
            "total = $359.94). Shipping: name='Bob Smith', address='456 Oak Ave', "
            "city='Shelbyville', zip='62565'."
        ),
        expected_tools=[
            "navigate", "fill_form", "submit_form", "add_to_cart",
            "update_cart_item", "remove_from_cart", "get_cart", "checkout",
        ],
        max_steps=25,
        outcome_checks=[
            {"type": "order_exists", "email": "bob@example.com"},
            # 239.97 + 129.99 + 79.96 = 449.92; SAVE20 = 89.984 → 89.98; total = 359.94
            {"type": "order_total", "email": "bob@example.com", "order_index": 0, "value": 359.94},
            {"type": "order_discount", "email": "bob@example.com", "order_index": 0, "value": 89.98},
            {"type": "order_coupon", "email": "bob@example.com", "order_index": 0, "value": "SAVE20"},
            {"type": "order_item_count", "email": "bob@example.com", "order_index": 0, "expected": 3},
            {"type": "cart_count", "email": "bob@example.com", "expected": 0},
        ],
    ),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 12. Cross-Category Search + Conditional Coupon
    #     Search for specific items across categories, apply coupon
    #     conditionally based on subtotal threshold.
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Scenario(
        id="cheapest_expensive_cross_category",
        prompt=(
            "Register with name='Cross Category', email='sc12@browser.test', "
            "password='Sc12Pass!'.\n\n"
            "Your task:\n"
            "  1. Search the 'Electronics' category and find the CHEAPEST product. Add it.\n"
            "  2. Search the 'Clothing' category and find the MOST EXPENSIVE product. Add it.\n"
            "  3. Search the 'Books' category and find the book with 'Pattern' in its name. Add it.\n\n"
            "After adding all three items, calculate the subtotal. If the subtotal exceeds "
            "$100, apply the SAVE20 coupon (20% off). If it's between $50 and $100, apply "
            "SAVE10 (10% off). If it's under $50, apply no coupon.\n\n"
            "Checkout with shipping: name='Cross Category', address='300 Cross St', "
            "city='MultiCity', zip='30003'.\n\n"
            "HINT: You must actually search each category and inspect the results to identify "
            "the correct products. Do not guess based on product names alone."
        ),
        expected_tools=[
            "navigate", "fill_form", "submit_form", "search_products",
            "add_to_cart", "checkout",
        ],
        max_steps=20,
        outcome_checks=[
            {"type": "user_exists", "email": "sc12@browser.test"},
            {"type": "order_exists", "email": "sc12@browser.test"},
            # Cheapest Electronics: USB-C Hub $34.99
            # Most expensive Clothing: Running Shoes $89.99
            # Book with "Pattern": Design Patterns $49.99
            # Subtotal: 34.99 + 89.99 + 49.99 = $174.97 (> $100 → SAVE20)
            # SAVE20: 20% of $174.97 = $34.99 (34.994 rounds to 34.99)
            # Total: $174.97 - $34.99 = $139.98
            {"type": "order_coupon", "email": "sc12@browser.test", "order_index": 0, "value": "SAVE20"},
            {"type": "order_discount", "email": "sc12@browser.test", "order_index": 0, "value": 34.99},
            {"type": "order_total", "email": "sc12@browser.test", "order_index": 0, "value": 139.98},
            {"type": "order_item_count", "email": "sc12@browser.test", "order_index": 0, "expected": 3},
        ],
    ),
]
