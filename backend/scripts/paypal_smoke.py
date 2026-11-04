"""Day-1 check: create and send one sandbox invoice end to end.

Usage (from backend/):  python -m scripts.paypal_smoke you-sandbox-buyer@example.com
Use the email of your SANDBOX personal account (developer.paypal.com > Sandbox accounts),
then log into sandbox.paypal.com as that buyer to pay it.
"""

import sys

import httpx

from app.services.paypal import paypal


def main() -> None:
    buyer = sys.argv[1] if len(sys.argv) > 1 else None
    if not buyer:
        sys.exit("Pass your sandbox buyer email as the first argument.")
    if not (paypal.client_id and paypal.secret):
        sys.exit("PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are empty. Fill them in backend/.env.")
    print("PayPal API:", paypal.base)

    try:
        inv = paypal.create_invoice(
            customer_name="Test Customer",
            customer_email=buyer,
            items=[{"name": "Smoke test deposit", "quantity": 1, "unit_amount_cents": 1000}],
            note="Open Tradesman smoke test",
        )
        print("Created:", inv["id"])
        paypal.send_invoice(inv["id"])
        detail = paypal.get_invoice(inv["id"])
    except httpx.HTTPStatusError as e:
        # PayPal puts the useful part (name, details[].issue) in the body.
        sys.exit(f"PayPal said {e.response.status_code} on {e.request.url.path}:\n{e.response.text}")

    print("Status:", detail.get("status"))
    print("Payer link:", detail.get("detail", {}).get("metadata", {}).get("recipient_view_url"))
    print("\nNext: log into https://www.sandbox.paypal.com as the buyer and pay it,")
    print(f"then re-check with:  python -c \"from app.services.paypal import paypal; print(paypal.get_invoice('{inv['id']}')['status'])\"")


if __name__ == "__main__":
    main()
