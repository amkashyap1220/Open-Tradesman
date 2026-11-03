"""Demo data: one Spanish-speaking handyman with a price book.

Runs automatically on startup when the database is empty.
TODO(Nov 9): add ~3 months of fake jobs, invoices, receipts and hours for the dashboard.
"""

from sqlmodel import Session, select

from .db import engine
from .models import PriceBookItem, Tradesperson

PRICE_BOOK = [
    # trade, name, unit, price in dollars
    ("labor", "Labor (lead)", "hour", 65),
    ("labor", "Labor (helper)", "hour", 35),
    ("drywall", "Patch drywall hole up to 12 in", "each", 95),
    ("drywall", "Replace drywall section (per sheet)", "sheet", 180),
    ("paint", "Paint walls, 2 coats (small room up to 100 sq ft floor)", "room", 350),
    ("paint", "Paint ceiling, 2 coats (small room)", "room", 175),
    ("paint", "Paint trim and baseboards", "linear ft", 3),
    ("paint", "Paint interior door, both sides", "each", 85),
    ("prep", "Prep and protect room (drop cloths, tape, move items)", "room", 60),
    ("materials", "Primer, per gallon", "gallon", 32),
    ("materials", "Interior paint, per gallon (if contractor supplies)", "gallon", 48),
    ("plumbing", "Replace vanity faucet (labor only)", "each", 140),
    ("cleanup", "Debris haul-away, small load", "each", 75),
]


def seed() -> None:
    with Session(engine) as session:
        if session.exec(select(Tradesperson)).first():
            return
        tp = Tradesperson(
            name="Miguel Torres",
            business_name="Torres Handyman Services",
            email="miguel@example.com",
            language="es",
            hourly_rate_cents=6500,
            markup_pct=15,
            deposit_pct=30,
        )
        session.add(tp)
        session.flush()
        for trade, name, unit, dollars in PRICE_BOOK:
            session.add(PriceBookItem(tradesperson_id=tp.id, trade=trade, name=name, unit=unit, price_cents=dollars * 100))
        session.commit()
