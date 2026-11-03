"""Money math in one place (integer cents)."""

from .models import Job, LineItem


def line_total(item: LineItem) -> int:
    return round(item.quantity * (item.unit_price_cents or 0))


def job_totals(job: Job, items: list[LineItem]) -> dict:
    subtotal = sum(line_total(i) for i in items)
    tax = round(subtotal * job.tax_rate_pct / 100)
    return {
        "subtotal_cents": subtotal,
        "tax_cents": tax,
        "total_cents": subtotal + tax,
        "needs_price": sum(1 for i in items if i.needs_price),
    }


def deposit_amount(total_cents: int, deposit_pct: float) -> int:
    return round(total_cents * deposit_pct / 100)
