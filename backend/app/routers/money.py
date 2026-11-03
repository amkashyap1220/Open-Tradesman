from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import Session, select

from ..db import get_session, readonly_engine
from ..deps import current_tradesperson
from ..models import Customer, Invoice, Job, Receipt, ReceiptLine, Tradesperson
from ..services import claude

router = APIRouter(prefix="/api", tags=["money"])


@router.get("/money/summary")
def summary(tp: Tradesperson = Depends(current_tradesperson), session: Session = Depends(get_session)):
    rows = session.exec(
        select(Invoice, Job, Customer)
        .join(Job, Invoice.job_id == Job.id)
        .join(Customer, Job.customer_id == Customer.id)
        .where(Job.tradesperson_id == tp.id)
    ).all()
    now = datetime.now(timezone.utc)
    open_invoices = [
        {
            "id": inv.id,
            "job_id": job.id,
            "customer": cust.name,
            "kind": inv.kind,
            "amount_cents": inv.amount_cents,
            "days_out": (now - inv.sent_at.replace(tzinfo=timezone.utc)).days if inv.sent_at else 0,
        }
        for inv, job, cust in rows
        if inv.status == "sent"
    ]
    paid_this_month = sum(
        inv.amount_cents
        for inv, _, _ in rows
        if inv.status == "paid" and inv.paid_at and inv.paid_at.month == now.month and inv.paid_at.year == now.year
    )
    return {
        "owed_cents": sum(i["amount_cents"] for i in open_invoices),
        "paid_this_month_cents": paid_this_month,
        "deposits_unpaid": sum(1 for i in open_invoices if i["kind"] == "deposit"),
        "open_invoices": sorted(open_invoices, key=lambda i: -i["days_out"]),
        # TODO(Nov 10): real hourly rate, profit per job, materials spend.
    }


class Ask(BaseModel):
    question: str


@router.post("/money/ask")
def ask(body: Ask, tp: Tradesperson = Depends(current_tradesperson)):
    try:
        sql = claude.question_to_sql(body.question, tp.id)
    except ValueError as e:
        raise HTTPException(400, f"Couldn't answer that safely: {e}")
    with readonly_engine.connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(sql))]
    answer = claude.phrase_answer(body.question, rows, tp.language)
    return {"answer": answer, "sql": sql, "rows": rows[:50]}


@router.post("/receipts")
async def upload_receipt(
    image: UploadFile, tp: Tradesperson = Depends(current_tradesperson), session: Session = Depends(get_session)
):
    open_jobs = session.exec(select(Job).where(Job.tradesperson_id == tp.id, Job.status != "paid")).all()
    data = await image.read()
    parsed = claude.read_receipt(
        data, image.content_type or "image/jpeg", [{"id": j.id, "title": j.title, "address": j.address} for j in open_jobs]
    )
    receipt = Receipt(tradesperson_id=tp.id, vendor=parsed["vendor"], total_cents=round(parsed["total"] * 100))
    session.add(receipt)
    session.flush()
    valid_ids = {j.id for j in open_jobs}
    for line in parsed["lines"]:
        job_id = line.get("suggested_job_id")
        session.add(
            ReceiptLine(
                receipt_id=receipt.id,
                job_id=job_id if job_id in valid_ids and not line["personal"] else None,
                description=line["description"],
                amount_cents=round(line["amount"] * 100),
                personal=line["personal"],
                confirmed=False,  # tradesperson confirms the split in the app
            )
        )
    session.commit()
    lines = session.exec(select(ReceiptLine).where(ReceiptLine.receipt_id == receipt.id)).all()
    return {"receipt": receipt, "lines": lines}
