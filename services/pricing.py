def calculate_line_total(unit_price, quantity):
    return round(unit_price * quantity, 2)


def calculate_order_total(line_totals):
    total = 0.0
    for lt in line_totals:
        total += lt
    return total


def apply_discount(total, discount_pct):
    if discount_pct < 0 or discount_pct > 100:
        raise ValueError("discount must be between 0 and 100")
    if discount_pct == 0:
        return total
    discount = round(total * (discount_pct / 100.0), 2)
    return round(total - discount, 2)


def calculate_tax(subtotal, tax_rate=8.875):
    return round(subtotal * (tax_rate / 100.0), 2)


def calculate_final_total(subtotal, tax_rate=8.875, discount_pct=0.0):
    after_discount = apply_discount(subtotal, discount_pct)
    tax = calculate_tax(after_discount, tax_rate)
    return round(after_discount + tax, 2)
