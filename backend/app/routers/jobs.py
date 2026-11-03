import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..deps import current_tradesperson
from ..models import AuditLog, Customer, Invoice, Job, LineItem, PriceBookItem, Tradesperson
from ..services import claude
from ..services.paypal import paypal
from ..services.stt import SpeechToTextUnavailable, transcribe
from ..totals import deposit_amount, job_totals, line_total

router = APIRouter(prefix="/api", tags=["jobs"])

UPLOADS = Path("uploads")  # TODO: move to object storage (Supabase Storage / R2) before deploying


@router.get("/me")
def me(tp: Tradesperson = Depends(current_tradesperson)):
    return tp


@router.get("/price-book")
def price_book(tp: Tradesperson = Depends(current_tradesperson), session: Session = Depends(get_session)):
    return session.exec(select(PriceBookItem).where(PriceBookItem.tradesperson_id == tp.id)).all()


# ---------------------------------------------------------------- jobs
class NewJob(BaseModel):
    customer_name: str
    customer_email: str
    customer_language: str = "en"
    title: str = ""
    address: str = ""
    billing_mode: str = "fixed"  # fixed or tm
    tax_rate_pct: float = 0.0


@router.post("/jobs")
def create_job(body: NewJob, tp: Tradesperson = Depends(current_tradesperson), session: Session = Depends(get_session)):
    if body.billing_mode not in ("fixed", "tm"):
        raise HTTPException(400, "billing_mode must be 'fixed' or 'tm'")
    customer = Customer(
        tradesperson_id=tp.id, name=body.customer_name, email=body.customer_email, language=body.customer_language
    )
    session.add(customer)
    session.flush()
    job = Job(
        tradesperson_id=tp.id,
        customer_id=customer.id,
        title=body.title,
        address=body.address,
        billing_mode=body.billing_mode,
        tax_rate_pct=body.tax_rate_pct,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.get("/jobs")
def list_jobs(tp: Tradesperson = Depends(current_tradesperson), session: Session = Depends(get_session)):
    jobs = session.exec(select(Job).where(Job.tradesperson_id == tp.id).order_by(Job.created_at.desc())).all()
    out = []
    for job in jobs:
        items = session.exec(select(LineItem).where(LineItem.job_id == job.id)).all()
        customer = session.get(Customer, job.customer_id)
        out.append({**job.model_dump(), "customer_name": customer.name, **job_totals(job, items)})
    return out


def _job_detail(job: Job, session: Session) -> dict:
    items = session.exec(select(LineItem).where(LineItem.job_id == job.id)).all()
    invoices = session.exec(select(Invoice).where(Invoice.job_id == job.id)).all()
    customer = session.get(Customer, job.customer_id)
    return {
        "job": job.model_dump(exclude={"ai_questions", "ai_assumptions"}),
        "customer": customer,
        "questions": json.loads(job.ai_questions),
        "assumptions": json.loads(job.ai_assumptions),
        "line_items": [{**i.model_dump(), "line_total_cents": line_total(i)} for i in items],
        "invoices": invoices,
        "totals": job_totals(job, items),
    }


def _get_job(job_id: int, tp: Tradesperson, session: Session) -> Job:
    job = session.get(Job, job_id)
    if not job or job.tradesperson_id != tp.id:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/jobs/{job_id}")
def get_job(job_id: int, tp: Tradesperson = Depends(current_tradesperson), session: Session = Depends(get_session)):
    return _job_detail(_get_job(job_id, tp, session), session)


# ---------------------------------------------------------------- walkthrough -> AI estimate
@router.post("/jobs/{job_id}/walkthrough")
async def walkthrough(
    job_id: int,
    audio: UploadFile | None = File(None),
    photos: list[UploadFile] = File(default_factory=list),
    notes: str = Form(""),
    tp: Tradesperson = Depends(current_tradesperson),
    session: Session = Depends(get_session),
):
    job = _get_job(job_id, tp, session)
    customer = session.get(Customer, job.customer_id)

    transcript = notes.strip()
    if audio is not None:
        try:
            spoken = transcribe(await audio.read())
            transcript = f"{spoken}\n{transcript}".strip()
        except SpeechToTextUnavailable as e:
            if not transcript:
                raise HTTPException(400, str(e))
    if not transcript:
        raise HTTPException(400, "Record a voice note or type what the job involves.")

    photo_data: list[tuple[bytes, str]] = []
    UPLOADS.mkdir(exist_ok=True)
    for p in photos:
        data = await p.read()
        photo_data.append((data, p.content_type or "image/jpeg"))
        (UPLOADS / f"job{job.id}-{uuid.uuid4().hex[:8]}-{p.filename}").write_bytes(data)

    book = session.exec(select(PriceBookItem).where(PriceBookItem.tradesperson_id == tp.id)).all()
    draft = claude.draft_estimate(
        transcript=transcript,
        photos=photo_data,
        price_book=[b.model_dump(exclude={"tradesperson_id"}) for b in book],
        tradesperson_lang=tp.language,
        customer_lang=customer.language,
        billing_mode=job.billing_mode,
    )

    # Replace previous AI lines (keep manual edits from the tradesperson).
    for old in session.exec(select(LineItem).where(LineItem.job_id == job.id, LineItem.source == "ai")).all():
        session.delete(old)
    for it in claude.apply_price_book(draft["line_items"], {b.id: b.price_cents for b in book}):
        session.add(LineItem(job_id=job.id, source="ai", **it))

    job.transcript = transcript
    job.title = job.title or draft["title"]["customer"]
    job.ai_questions = json.dumps(draft.get("questions", []), ensure_ascii=False)
    job.ai_assumptions = json.dumps(draft.get("assumptions", []), ensure_ascii=False)
    session.add(AuditLog(job_id=job.id, actor="system", action="ai_draft_estimate"))
    session.commit()
    return _job_detail(job, session)


class LineItemPatch(BaseModel):
    quantity: float | None = None
    unit_price_cents: int | None = None
    text_tradesperson: str | None = None
    text_customer: str | None = None


@router.patch("/line-items/{item_id}")
def edit_line_item(
    item_id: int, body: LineItemPatch, tp: Tradesperson = Depends(current_tradesperson), session: Session = Depends(get_session)
):
    item = session.get(LineItem, item_id)
    if not item:
        raise HTTPException(404, "Line item not found")
    _get_job(item.job_id, tp, session)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    if body.unit_price_cents is not None:
        item.needs_price = False
        item.source = "manual"
    session.add(AuditLog(job_id=item.job_id, actor="tradesperson", action="edit_line_item", detail=str(item_id)))
    session.commit()
    return item


# ---------------------------------------------------------------- send estimate + deposit invoice
@router.post("/jobs/{job_id}/send")
def send_estimate(job_id: int, tp: Tradesperson = Depends(current_tradesperson), session: Session = Depends(get_session)):
    job = _get_job(job_id, tp, session)
    items = session.exec(select(LineItem).where(LineItem.job_id == job.id)).all()
    totals = job_totals(job, items)
    if not items:
        raise HTTPException(400, "The estimate has no line items yet.")
    if totals["needs_price"]:
        raise HTTPException(400, f"{totals['needs_price']} item(s) still need a price before sending.")

    customer = session.get(Customer, job.customer_id)
    deposit = deposit_amount(totals["total_cents"], tp.deposit_pct)
    label = f"Deposit ({tp.deposit_pct:g}%) - {job.title or 'Job'} #{job.id}"
    note = "\n".join(f"- {i.text_customer} x {i.quantity:g}" for i in items)

    created = paypal.create_invoice(
        customer_name=customer.name,
        customer_email=customer.email,
        items=[{"name": label, "quantity": 1, "unit_amount_cents": deposit}],
        note=f"Estimate total: ${totals['total_cents'] / 100:,.2f}\n{note}",
    )
    paypal.send_invoice(created["id"])
    detail = paypal.get_invoice(created["id"])

    invoice = Invoice(
        job_id=job.id,
        kind="deposit",
        amount_cents=deposit,
        paypal_invoice_id=created["id"],
        payer_url=detail.get("detail", {}).get("metadata", {}).get("recipient_view_url", ""),
        status="sent",
        sent_at=datetime.now(timezone.utc),
    )
    job.status = "estimate_sent"
    session.add(invoice)
    session.add(AuditLog(job_id=job.id, actor="tradesperson", action="send_estimate", detail=created["id"]))
    session.commit()
    return _job_detail(job, session)


@router.post("/invoices/{invoice_id}/remind")
def remind(invoice_id: int, tp: Tradesperson = Depends(current_tradesperson), session: Session = Depends(get_session)):
    inv = session.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    _get_job(inv.job_id, tp, session)
    paypal.remind(inv.paypal_invoice_id)
    session.add(AuditLog(job_id=inv.job_id, actor="tradesperson", action="remind", detail=inv.paypal_invoice_id))
    session.commit()
    return {"ok": True}

# TODO(Nov 8): change orders (create, customer approve), time entries.
# TODO(Nov 9): final invoice (fixed: quoted total + approved change orders - deposit;
#              tm: hours x rate + receipts x (1 + markup) - deposit).
# TODO: customer-facing view (signed link, customer-language text only, approve buttons).
