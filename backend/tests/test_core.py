"""Tests run without network: Claude and PayPal are mocked."""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
if os.path.exists("test.db"):
    os.remove("test.db")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import jobs as jobs_router
from app.routers.webhooks import mark_invoice_paid
from app.services import claude
from app.db import engine
from sqlmodel import Session


# ---------------------------------------------------------------- pure guardrails
def test_price_book_is_the_only_source_of_prices():
    draft = [
        {"kind": "labor", "text_tradesperson": "a", "text_customer": "a", "quantity": 2, "unit": "hour", "price_book_item_id": 1},
        {"kind": "flat", "text_tradesperson": "b", "text_customer": "b", "quantity": 1, "unit": "each", "price_book_item_id": None},
        {"kind": "flat", "text_tradesperson": "c", "text_customer": "c", "quantity": 1, "unit": "each", "price_book_item_id": 999},
    ]
    out = claude.apply_price_book(draft, {1: 6500})
    assert out[0]["unit_price_cents"] == 6500 and not out[0]["needs_price"]
    assert out[1]["unit_price_cents"] is None and out[1]["needs_price"]
    assert out[2]["unit_price_cents"] is None and out[2]["needs_price"]  # unknown id is not trusted


@pytest.mark.parametrize(
    "bad",
    [
        "DELETE FROM job",
        "select 1; drop table job",
        "UPDATE invoice SET status='paid'",
        "WITH x AS (SELECT 1) DELETE FROM job",
        "PRAGMA table_info(job)",
    ],
)
def test_guard_sql_rejects_writes(bad):
    with pytest.raises(ValueError):
        claude.guard_sql(bad)


def test_guard_sql_adds_limit():
    assert claude.guard_sql("SELECT * FROM job;").endswith("LIMIT 200")
    assert claude.guard_sql("select 1 limit 5") == "select 1 limit 5"


# ---------------------------------------------------------------- API flow
FAKE_DRAFT = {
    "title": {"tradesperson": "Baño", "customer": "Bathroom repair"},
    "line_items": [
        {"kind": "flat", "text_tradesperson": "Parchar hoyo", "text_customer": "Patch drywall hole", "quantity": 2, "unit": "each", "price_book_item_id": 3},
        {"kind": "flat", "text_tradesperson": "Algo raro", "text_customer": "Something odd", "quantity": 1, "unit": "each", "price_book_item_id": None},
    ],
    "assumptions": [{"tradesperson": "2 manos", "customer": "2 coats"}],
    "questions": [{"tradesperson": "¿Incluye la puerta?", "customer": "Door included?"}],
}


class FakePayPal:
    def create_invoice(self, **kw):
        self.created = kw
        return {"id": "INV2-TEST-0001"}

    def send_invoice(self, invoice_id):
        return {}

    def get_invoice(self, invoice_id):
        return {"detail": {"metadata": {"recipient_view_url": "https://sandbox.example/pay"}}}


def test_walkthrough_edit_send_and_webhook(monkeypatch):
    monkeypatch.setattr(claude, "draft_estimate", lambda **kw: FAKE_DRAFT)
    fake = FakePayPal()
    monkeypatch.setattr(jobs_router, "paypal", fake)

    with TestClient(app) as c:
        job = c.post(
            "/api/jobs",
            json={"customer_name": "Ann Lee", "customer_email": "ann@example.com", "billing_mode": "fixed"},
        ).json()

        d = c.post(f"/api/jobs/{job['id']}/walkthrough", data={"notes": "dos hoyos en la pared"}).json()
        assert d["totals"]["needs_price"] == 1
        assert d["questions"][0]["customer"] == "Door included?"

        # Can't send while an item has no price
        r = c.post(f"/api/jobs/{job['id']}/send")
        assert r.status_code == 400

        unpriced = next(i for i in d["line_items"] if i["needs_price"])
        c.patch(f"/api/line-items/{unpriced['id']}", json={"unit_price_cents": 5000})

        d = c.post(f"/api/jobs/{job['id']}/send").json()
        # 2 x $95 + $50 = $240 total, 30% deposit = $72
        assert d["totals"]["total_cents"] == 24000
        assert d["invoices"][0]["amount_cents"] == 7200
        assert d["job"]["status"] == "estimate_sent"

        with Session(engine) as s:
            mark_invoice_paid("INV2-TEST-0001", s)
        d = c.get(f"/api/jobs/{job['id']}").json()
        assert d["job"]["status"] == "deposit_paid"

        summary = c.get("/api/money/summary").json()
        assert summary["paid_this_month_cents"] == 7200
