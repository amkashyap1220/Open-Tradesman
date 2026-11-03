"""All Claude calls live here.

Every call forces a tool with a JSON schema, so the backend always gets structured
data back instead of prose to parse. Guardrails (prices, SQL) are enforced in plain
Python AFTER the model answers, never trusted to the prompt alone.
"""

import base64
import json
import re
from typing import Any

import anthropic

from ..config import get_settings

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
    return _client


def _call_tool(model: str, system: str, content: list[dict], tool: dict, max_tokens: int = 4096) -> dict:
    resp = client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": content}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Claude did not return the expected tool call")


def _image_block(data: bytes, media_type: str) -> dict:
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": base64.b64encode(data).decode()},
    }


# --------------------------------------------------------------------------
# 1. Draft an estimate from a walkthrough
# --------------------------------------------------------------------------
BILINGUAL = {
    "type": "object",
    "properties": {"tradesperson": {"type": "string"}, "customer": {"type": "string"}},
    "required": ["tradesperson", "customer"],
}

ESTIMATE_TOOL = {
    "name": "record_estimate",
    "description": "Record a draft job estimate built from the tradesperson's walkthrough.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": BILINGUAL,
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string", "enum": ["labor", "material", "flat"]},
                        "text_tradesperson": {"type": "string"},
                        "text_customer": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit": {"type": "string"},
                        "price_book_item_id": {
                            "type": ["integer", "null"],
                            "description": "id of the matching price book item, or null if nothing matches",
                        },
                        "low_confidence_translation": {"type": "boolean"},
                    },
                    "required": ["kind", "text_tradesperson", "text_customer", "quantity", "unit", "price_book_item_id"],
                },
            },
            "assumptions": {"type": "array", "items": BILINGUAL},
            "questions": {
                "type": "array",
                "items": BILINGUAL,
                "description": "1-3 questions about scope gaps the tradesperson should answer before sending",
            },
        },
        "required": ["title", "line_items", "assumptions", "questions"],
    },
}

ESTIMATE_SYSTEM = """You turn a tradesperson's job walkthrough into an itemized estimate.

Rules:
- Use ONLY items from the price book. Reference them by id. If nothing fits, set price_book_item_id to null; never guess a price.
- Never invent measurements. Quantities come from the transcript. If a needed dimension or count is missing, add a question instead.
- Photos are context only. Do not estimate sizes from photos.
- Write text_tradesperson in the tradesperson's language and text_customer in the customer's language. Use the plain trade term a homeowner would understand. Set low_confidence_translation=true when a trade term has no clear equivalent.
- List every assumption you made (e.g. "2 coats", "customer supplies paint").
- Ask at most 3 questions, only about things that change the price or scope."""


def draft_estimate(
    *,
    transcript: str,
    photos: list[tuple[bytes, str]],
    price_book: list[dict],
    tradesperson_lang: str,
    customer_lang: str,
    billing_mode: str,
) -> dict:
    content: list[dict] = [_image_block(data, mt) for data, mt in photos[:6]]
    content.append(
        {
            "type": "text",
            "text": (
                f"Tradesperson language: {tradesperson_lang}\nCustomer language: {customer_lang}\n"
                f"Billing mode: {'fixed price' if billing_mode == 'fixed' else 'time and materials'}\n\n"
                f"Price book (JSON):\n{json.dumps(price_book, ensure_ascii=False)}\n\n"
                f"Walkthrough transcript:\n{transcript}"
            ),
        }
    )
    return _call_tool(get_settings().claude_model_smart, ESTIMATE_SYSTEM, content, ESTIMATE_TOOL)


def apply_price_book(draft_items: list[dict], price_book: dict[int, int]) -> list[dict]:
    """Guardrail: prices come ONLY from the price book.

    price_book maps item id -> price in cents. Any item whose id is missing or
    unknown is marked needs_price and gets no price, which blocks sending.
    """
    out = []
    for it in draft_items:
        pid = it.get("price_book_item_id")
        price = price_book.get(pid) if isinstance(pid, int) else None
        out.append(
            {
                "kind": it.get("kind", "flat"),
                "text_tradesperson": it.get("text_tradesperson", ""),
                "text_customer": it.get("text_customer", ""),
                "quantity": float(it.get("quantity") or 1),
                "unit": it.get("unit", "each"),
                "price_book_item_id": pid if price is not None else None,
                "unit_price_cents": price,
                "needs_price": price is None,
                "low_confidence": bool(it.get("low_confidence_translation", False)),
            }
        )
    return out


# --------------------------------------------------------------------------
# 2. Read a receipt photo
# --------------------------------------------------------------------------
RECEIPT_TOOL = {
    "name": "record_receipt",
    "description": "Record what a materials receipt contains and suggest which job each line belongs to.",
    "input_schema": {
        "type": "object",
        "properties": {
            "vendor": {"type": "string"},
            "date": {"type": ["string", "null"], "description": "YYYY-MM-DD"},
            "total": {"type": "number"},
            "lines": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "amount": {"type": "number"},
                        "suggested_job_id": {"type": ["integer", "null"]},
                        "personal": {"type": "boolean", "description": "true for snacks, drinks, personal items"},
                    },
                    "required": ["description", "amount", "suggested_job_id", "personal"],
                },
            },
        },
        "required": ["vendor", "date", "total", "lines"],
    },
}


def read_receipt(image: bytes, media_type: str, open_jobs: list[dict]) -> dict:
    content = [
        _image_block(image, media_type),
        {
            "type": "text",
            "text": "Open jobs (JSON):\n"
            + json.dumps(open_jobs, ensure_ascii=False)
            + "\n\nRead this receipt. Suggest a job per line only when it clearly fits; otherwise null.",
        },
    ]
    return _call_tool(get_settings().claude_model_smart, "You read materials receipts for tradespeople.", content, RECEIPT_TOOL)


# --------------------------------------------------------------------------
# 3. "Ask anything" about money (text-to-SQL)
# --------------------------------------------------------------------------
SQL_TOOL = {
    "name": "run_query",
    "description": "A single read-only SQL SELECT that answers the question.",
    "input_schema": {
        "type": "object",
        "properties": {"sql": {"type": "string"}},
        "required": ["sql"],
    },
}

ANSWER_TOOL = {
    "name": "answer",
    "description": "Answer the question from the query results.",
    "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
}

SCHEMA_HINT = """Tables (money is integer cents; divide by 100 for dollars):
job(id, tradesperson_id, customer_id, title, status, billing_mode, created_at)
customer(id, name, language)
lineitem(id, job_id, kind, quantity, unit_price_cents, change_order_id)
invoice(id, job_id, kind, amount_cents, status, sent_at, paid_at)  -- status: draft, sent, paid
receipt(id, vendor, purchased_on, total_cents)
receiptline(id, receipt_id, job_id, description, amount_cents, personal)
timeentry(id, job_id, person, hours, worked_on)
Only include rows for tradesperson_id = {tp_id} (join through job where needed)."""

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|grant|revoke|truncate|attach|pragma|copy|vacuum)\b", re.I
)


def guard_sql(sql: str) -> str:
    """Allow exactly one SELECT (or WITH ... SELECT). Adds a row limit."""
    s = sql.strip().rstrip(";").strip()
    if ";" in s:
        raise ValueError("Only one statement is allowed")
    if not re.match(r"^(select|with)\b", s, re.I):
        raise ValueError("Only SELECT queries are allowed")
    if _FORBIDDEN.search(s):
        raise ValueError("Query contains a forbidden keyword")
    if not re.search(r"\blimit\s+\d+\s*$", s, re.I):
        s += " LIMIT 200"
    return s


def question_to_sql(question: str, tp_id: int) -> str:
    sql = _call_tool(
        get_settings().claude_model_fast,
        "You write one SQL SELECT for SQLite/Postgres-compatible syntax.\n" + SCHEMA_HINT.format(tp_id=tp_id),
        [{"type": "text", "text": question}],
        SQL_TOOL,
        max_tokens=1024,
    )["sql"]
    return guard_sql(sql)


def phrase_answer(question: str, rows: list[dict[str, Any]], language: str) -> str:
    return _call_tool(
        get_settings().claude_model_fast,
        f"Answer briefly in the language '{language}', using only the numbers in the results. "
        "Show money as dollars. If results are empty, say there's nothing matching.",
        [{"type": "text", "text": f"Question: {question}\nResults (JSON): {json.dumps(rows, default=str)}"}],
        ANSWER_TOOL,
        max_tokens=512,
    )["text"]
