from fastapi import Depends, HTTPException
from sqlmodel import Session, select

from .db import get_session
from .models import Tradesperson


def current_tradesperson(session: Session = Depends(get_session)) -> Tradesperson:
    # TODO(auth): single demo tradesperson for the hackathon. Add real sign-in later.
    tp = session.exec(select(Tradesperson)).first()
    if not tp:
        raise HTTPException(500, "No tradesperson found. Run the seed (it runs on startup when the DB is empty).")
    return tp
