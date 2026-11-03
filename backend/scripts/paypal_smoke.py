"""Day-1 check: create and send one sandbox invoice end to end.

Usage (from backend/):  python -m scripts.paypal_smoke you-sandbox-buyer@example.com
Use the email of your SANDBOX personal account (developer.paypal.com > Sandbox accounts),
then log into sandbox.paypal.com as that buyer to pay it.
"""

import sys

from app.services.paypal import paypal


def main() -> None:
    buyer = sys.argv[1] if len(sys.argv) > 1 else None
    if not buyer:
        sys.exit("Pass your sandbox buyer email as the first argument.")
    inv = paypal.create_invoice(
        customer_name="Test Customer",
        customer_email=buyer,
        items=[{"name": "Smoke test deposit", "quantity": 1, "unit_amount_cents": 1000}],
        note="PayPal Tradesman smoke test",
    )
    print("Created:", inv["id"])
    paypal.send_invoice(inv["id"])
    detail = paypal.get_invoice(inv["id"])
    print("Status:", detail.get("status"))
    print("Payer link:", detail.get("detail", {}).get("metadata", {}).get("recipient_view_url"))


if __name__ == "__main__":
    main()
