"""Database tables. Money is stored as integer cents to avoid float rounding."""

from datetime import date, datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


class Tradesperson(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    business_name: str = ""
    email: str = ""
    language: str = "es"  # language the tradesperson works in
    hourly_rate_cents: int = 6500
    markup_pct: float = 15.0  # applied to materials on time-and-materials jobs
    deposit_pct: float = 30.0


class PriceBookItem(SQLModel, table=True):
    """The ONLY source of prices. The AI may pick items, never invent rates."""

    id: Optional[int] = Field(default=None, primary_key=True)
    tradesperson_id: int = Field(foreign_key="tradesperson.id")
    trade: str  # e.g. drywall, paint
    name: str  # e.g. "Patch drywall hole up to 12 in"
    unit: str  # each, hour, sq ft, gallon
    price_cents: int


class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tradesperson_id: int = Field(foreign_key="tradesperson.id")
    name: str
    email: str
    language: str = "en"


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tradesperson_id: int = Field(foreign_key="tradesperson.id")
    customer_id: int = Field(foreign_key="customer.id")
    title: str = ""
    address: str = ""
    # draft -> estimate_sent -> deposit_paid -> in_progress -> invoiced -> paid
    status: str = "draft"
    billing_mode: str = "fixed"  # "fixed" or "tm" (time and materials)
    tax_rate_pct: float = 0.0
    transcript: str = ""
    ai_questions: str = "[]"  # JSON list of {tradesperson, customer}
    ai_assumptions: str = "[]"  # JSON list of {tradesperson, customer}
    created_at: datetime = Field(default_factory=now)


class LineItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id")
    change_order_id: Optional[int] = Field(default=None, foreign_key="changeorder.id")
    kind: str  # labor, material, flat
    text_tradesperson: str
    text_customer: str
    quantity: float = 1.0
    unit: str = "each"
    price_book_item_id: Optional[int] = Field(default=None, foreign_key="pricebookitem.id")
    unit_price_cents: Optional[int] = None  # None = needs price; blocks sending
    needs_price: bool = False
    low_confidence: bool = False  # translation flagged as uncertain
    source: str = "ai"  # ai or manual


class ChangeOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id")
    description_tradesperson: str
    description_customer: str
    photo_path: str = ""
    status: str = "pending"  # pending, approved, declined
    approved_at: Optional[datetime] = None


class Receipt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tradesperson_id: int = Field(foreign_key="tradesperson.id")
    vendor: str = ""
    purchased_on: Optional[date] = None
    total_cents: int = 0
    image_path: str = ""


class ReceiptLine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    receipt_id: int = Field(foreign_key="receipt.id")
    job_id: Optional[int] = Field(default=None, foreign_key="job.id")  # None = unassigned
    description: str
    amount_cents: int
    personal: bool = False
    confirmed: bool = False


class TimeEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id")
    person: str
    hours: float
    worked_on: date


class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id")
    kind: str  # deposit, change, final
    amount_cents: int
    paypal_invoice_id: str = ""
    payer_url: str = ""
    status: str = "draft"  # draft, sent, paid
    sent_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: Optional[int] = Field(default=None, foreign_key="job.id")
    actor: str  # tradesperson, customer, system, paypal
    action: str
    detail: str = ""
    at: datetime = Field(default_factory=now)
