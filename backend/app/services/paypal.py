"""PayPal Invoicing API v2 client (sandbox by default).

Docs: https://developer.paypal.com/docs/api/invoicing/v2/
Flow per invoice: generate number -> create draft -> send -> (customer pays) -> webhook.
"""

import json
import time

import httpx

from ..config import get_settings


def cents_to_str(cents: int) -> str:
    return f"{cents / 100:.2f}"


class PayPalClient:
    def __init__(self) -> None:
        s = get_settings()
        self.base = s.paypal_base_url.rstrip("/")
        self.client_id = s.paypal_client_id
        self.secret = s.paypal_client_secret
        self.webhook_id = s.paypal_webhook_id
        self._token: str | None = None
        self._token_expires = 0.0

    # --- auth -------------------------------------------------------------
    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        r = httpx.post(
            f"{self.base}/v1/oauth2/token",
            auth=(self.client_id, self.secret),
            data={"grant_type": "client_credentials"},
            timeout=20,
        )
        r.raise_for_status()
        body = r.json()
        self._token = body["access_token"]
        self._token_expires = time.time() + body.get("expires_in", 3000)
        return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    # --- invoices ---------------------------------------------------------
    def next_invoice_number(self) -> str:
        r = httpx.post(f"{self.base}/v2/invoicing/generate-next-invoice-number", headers=self._headers(), timeout=20)
        r.raise_for_status()
        return r.json()["invoice_number"]

    def create_invoice(
        self,
        *,
        customer_name: str,
        customer_email: str,
        items: list[dict],  # [{"name": str, "quantity": float, "unit_amount_cents": int}]
        note: str = "",
        currency: str = "USD",
    ) -> dict:
        given, _, surname = customer_name.partition(" ")
        payload = {
            "detail": {
                "invoice_number": self.next_invoice_number(),
                "currency_code": currency,
                "note": note[:4000],
            },
            "primary_recipients": [
                {
                    "billing_info": {
                        "email_address": customer_email,
                        "name": {"given_name": given or customer_name, "surname": surname},
                    }
                }
            ],
            "items": [
                {
                    "name": it["name"][:200],
                    "quantity": f"{it['quantity']:g}",
                    "unit_amount": {"currency_code": currency, "value": cents_to_str(it["unit_amount_cents"])},
                }
                for it in items
            ],
        }
        r = httpx.post(f"{self.base}/v2/invoicing/invoices", headers=self._headers(), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def send_invoice(self, invoice_id: str) -> dict:
        r = httpx.post(
            f"{self.base}/v2/invoicing/invoices/{invoice_id}/send",
            headers=self._headers(),
            json={"send_to_invoicer": False, "send_to_recipient": True},
            timeout=30,
        )
        r.raise_for_status()
        return r.json() if r.content else {}

    def get_invoice(self, invoice_id: str) -> dict:
        r = httpx.get(f"{self.base}/v2/invoicing/invoices/{invoice_id}", headers=self._headers(), timeout=20)
        r.raise_for_status()
        return r.json()

    def remind(self, invoice_id: str, note: str = "") -> None:
        r = httpx.post(
            f"{self.base}/v2/invoicing/invoices/{invoice_id}/remind",
            headers=self._headers(),
            json={"note": note} if note else {},
            timeout=20,
        )
        r.raise_for_status()

    # --- webhooks ---------------------------------------------------------
    def verify_webhook(self, headers: dict, raw_body: bytes) -> bool:
        """Ask PayPal whether a webhook really came from PayPal.

        The event goes back to PayPal as the exact bytes we received. Parsing and
        re-serializing it can change spacing, number formats or escaping, and then the
        signature check fails even for genuine events.
        """
        if not self.webhook_id:
            return False  # not configured: refuse rather than trust unsigned events
        h = {k.lower(): v for k, v in headers.items()}
        fields = {
            "auth_algo": h.get("paypal-auth-algo"),
            "cert_url": h.get("paypal-cert-url"),
            "transmission_id": h.get("paypal-transmission-id"),
            "transmission_sig": h.get("paypal-transmission-sig"),
            "transmission_time": h.get("paypal-transmission-time"),
            "webhook_id": self.webhook_id,
        }
        body = json.dumps(fields)[:-1] + ', "webhook_event": ' + raw_body.decode("utf-8") + "}"
        r = httpx.post(
            f"{self.base}/v1/notifications/verify-webhook-signature",
            headers=self._headers(),
            content=body.encode("utf-8"),
            timeout=20,
        )
        return r.status_code == 200 and r.json().get("verification_status") == "SUCCESS"


def invoice_id_from_event(event: dict) -> str | None:
    """INVOICING.* events carry the invoice under resource.invoice (older payloads: resource)."""
    res = event.get("resource") or {}
    inv = res.get("invoice") if isinstance(res.get("invoice"), dict) else res
    return inv.get("id")


paypal = PayPalClient()
