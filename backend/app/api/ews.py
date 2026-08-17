"""
GraphGuard Early Warning Signals (EWS) API Routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.models.models import EWSSignal
from backend.app.schemas.schemas import EWSSignalOut

router = APIRouter(prefix="/ews", tags=["Early Warning Signals"])

@router.get("", response_model=List[EWSSignalOut])
def get_ews_signals(
    account_id: Optional[str] = None,
    signal_code: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(EWSSignal)
    if account_id:
        query = query.filter(EWSSignal.account_id == account_id)
    if signal_code:
        query = query.filter(EWSSignal.signal_code == signal_code)

    offset = (page - 1) * limit
    return query.order_by(EWSSignal.triggered_at.desc()).offset(offset).limit(limit).all()

@router.get("/{ews_id}", response_model=EWSSignalOut)
def get_ews_signal_detail(ews_id: int, db: Session = Depends(get_db)):
    signal = db.query(EWSSignal).filter(EWSSignal.id == ews_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail=f"EWS Signal #{ews_id} not found")
    return signal
