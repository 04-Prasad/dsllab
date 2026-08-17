"""
GraphGuard Transactions API Routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.models.models import Transaction
from backend.app.schemas.schemas import TransactionOut

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.get("", response_model=List[TransactionOut])
def get_transactions(
    account_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(Transaction)
    if account_id:
        query = query.filter(
            (Transaction.sender_account_id == account_id) | (Transaction.receiver_account_id == account_id)
        )
    
    offset = (page - 1) * limit
    return query.order_by(Transaction.timestamp.desc()).offset(offset).limit(limit).all()

@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction_detail(transaction_id: str, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
    return tx
