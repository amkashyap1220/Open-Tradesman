import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from ..db import get_session
from ..models import AuditLog, Invoice, Job
from ..services.paypal import invoice_id_from_event, paypal

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def mark_invoice_paid(paypal_invoice_id: str, session: Session) -> Invoice | None:
    inv = session.exec(select(Invoice).where(Invoice.paypal_invoice_id == paypal_invoice_id)).first()
    if not inv or inv.status == "paid":
        return inv
    inv.status = "paid"
    inv.paid_at = datetime.now(timezone.utc)
    job = session.get(Job, inv.job_id)
    if inv.kind == "deposit" and job.status == "estimate_sent":
        job.status = "deposit_paid"
    elif inv.kind == "final":
        job.status = "paid"
    session.add(AuditLog(job_id=inv.job_id, actor="paypal", action="invoice_paid", detail=paypal_invoice_id))
    session.commit()
    return inv


@router.post("/paypal")
async def paypal_webhook(request: Request, session: Session = Depends(get_session)):
    raw = await request.body()
    if not paypal.verify_webhook(dict(request.headers), raw):
        raise HTTPException(400, "Webhook signature check failed")
    event = json.loads(raw)
    if event.get("event_type") == "INVOICING.INVOICE.PAID":
        inv_id = invoice_id_from_event(event)
        if inv_id:
            mark_invoice_paid(inv_id, session)
    return {"received": True}
