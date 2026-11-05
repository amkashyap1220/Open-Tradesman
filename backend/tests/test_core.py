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
        {"kind": "labor", "text_es": "a", "text_en": "a", "text_customer": "a", "quantity": 2, "unit": "hour", "price_book_item_id": 1},
        {"kind": "flat", "text_es": "b", "text_en": "b", "text_customer": "b", "quantity": 1, "unit": "each", "price_book_item_id": None},
        {"kind": "flat", "text_es": "c", "text_en": "c", "text_customer": "c", "quantity": 1, "unit": "each", "price_book_item_id": 999},
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
    "title": {"es": "Baño", "en": "Bathroom", "customer": "Bathroom repair"},
    "line_items": [
        {"kind": "flat", "text_es": "Parchar hoyo", "text_en": "Patch hole", "text_customer": "Patch drywall hole", "quantity": 2, "unit": "each", "price_book_item_id": 3},
        {"kind": "flat", "text_es": "Algo raro", "text_en": "Something odd", "text_customer": "Something odd", "quantity": 1, "unit": "each", "price_book_item_id": None},
    ],
    "assumptions": [{"es": "2 manos", "en": "2 coats", "customer": "2 coats"}],
    "questions": [{"es": "¿Incluye la puerta?", "en": "Include the door?", "customer": "Door included?"}],
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


# ---------------------------------------------------------------- structured outputs
def test_strict_schema_closes_every_object():
    s = claude.strict_schema(claude.ESTIMATE_TOOL["input_schema"])
    assert s["additionalProperties"] is False
    item = s["properties"]["line_items"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == set(item["properties"])  # optional fields become required
    assert s["properties"]["title"]["additionalProperties"] is False
    # the original schema is not mutated
    assert "additionalProperties" not in claude.ESTIMATE_TOOL["input_schema"]


class _Block:
    def __init__(self, type_, text=""):
        self.type, self.text = type_, text


class _Resp:
    def __init__(self, stop_reason, blocks):
        self.stop_reason, self.content = stop_reason, blocks


def _fake_client(resp, seen):
    class Messages:
        def create(self, **kw):
            seen.update(kw)
            return resp

    class Beta:
        messages = Messages()

    class C:
        messages = Messages()
        beta = Beta()

    return C()


def test_structured_parses_json_and_sends_schema(monkeypatch):
    seen = {}
    resp = _Resp("end_turn", [_Block("thinking"), _Block("text", '{"sql": "select 1"}')])
    monkeypatch.setattr(claude, "client", lambda: _fake_client(resp, seen))
    out = claude._structured("claude-haiku-5-5", "sys", [], claude.SQL_TOOL, effort="low")
    assert out == {"sql": "select 1"}
    assert "tool_choice" not in seen and "tools" not in seen
    assert seen["output_config"]["format"]["type"] == "json_schema"
    assert seen["output_config"]["effort"] == "low"


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_structured_raises_on_unusable_answer(monkeypatch, stop):
    resp = _Resp(stop, [_Block("text", "{")])
    monkeypatch.setattr(claude, "client", lambda: _fake_client(resp, {}))
    with pytest.raises(claude.ClaudeUnavailable):
        claude._structured("claude-sonnet-5-5", "sys", [], claude.SQL_TOOL)


# ---------------------------------------------------------------- both app languages
def test_ai_text_is_stored_in_both_app_languages(monkeypatch):
    monkeypatch.setattr(claude, "draft_estimate", lambda **kw: FAKE_DRAFT)
    with TestClient(app) as c:
        assert c.patch("/api/me", json={"language": "fr"}).status_code == 422  # only es / en
        assert c.patch("/api/me", json={"language": "en"}).json()["language"] == "en"
        assert c.get("/api/me").json()["language"] == "en"
        c.patch("/api/me", json={"language": "es"})  # leave the shared test DB as seeded

        job = c.post("/api/jobs", json={"customer_name": "Bo Kim", "customer_email": "bo@example.com"}).json()
        d = c.post(f"/api/jobs/{job['id']}/walkthrough", data={"notes": "dos hoyos"}).json()
        assert (d["job"]["title_es"], d["job"]["title_en"]) == ("Baño", "Bathroom")
        assert d["questions"][0]["en"] == "Include the door?"
        item = d["line_items"][0]
        assert (item["text_es"], item["text_en"]) == ("Parchar hoyo", "Patch hole")

        # Text the tradesperson types is theirs: stored as typed in both, never translated.
        item = c.patch(f"/api/line-items/{item['id']}", json={"text_tradesperson": "Parche grande"}).json()
        assert item["text_es"] == item["text_en"] == "Parche grande"


def test_typed_title_is_not_translated():
    with TestClient(app) as c:
        job = c.post("/api/jobs", json={"customer_name": "Al", "customer_email": "al@example.com", "title": "Casa de Al"}).json()
        assert job["title_es"] == job["title_en"] == "Casa de Al"


# ---------------------------------------------------------------- database URLs
@pytest.mark.parametrize(
    "given,expected",
    [
        ("postgres://u:p@h/db?sslmode=require", "postgresql+psycopg://u:p@h/db?sslmode=require"),
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("sqlite:///./dev.db", "sqlite:///./dev.db"),
    ],
)
def test_database_url_uses_psycopg3(given, expected):
    from app.db import normalize_url

    assert normalize_url(given) == expected


def test_postgres_engine_builds_without_connecting():
    from app.db import make_engine

    e = make_engine("postgres://u:p@example.invalid/db?sslmode=require")
    assert e.dialect.driver == "psycopg" and e.pool._pre_ping


def test_init_db_uses_direct_url_for_ddl(monkeypatch, tmp_path):
    import app.db as db

    direct = tmp_path / "direct.db"
    monkeypatch.setattr(db._settings, "database_url_unpooled", f"sqlite:///{direct}")
    db.init_db()
    from sqlalchemy import create_engine, inspect

    assert "job" in inspect(create_engine(f"sqlite:///{direct}")).get_table_names()


def test_line_items_keep_their_order_after_an_edit(monkeypatch):
    monkeypatch.setattr(claude, "draft_estimate", lambda **kw: FAKE_DRAFT)
    with TestClient(app) as c:
        job = c.post("/api/jobs", json={"customer_name": "Cy", "customer_email": "cy@example.com"}).json()
        d = c.post(f"/api/jobs/{job['id']}/walkthrough", data={"notes": "x"}).json()
        ids = [i["id"] for i in d["line_items"]]
        assert ids == sorted(ids)
        c.patch(f"/api/line-items/{ids[0]}", json={"text_tradesperson": "editado"})
        assert [i["id"] for i in c.get(f"/api/jobs/{job['id']}").json()["line_items"]] == ids
