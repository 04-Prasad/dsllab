"""
GraphGuard Accounts API Routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.db.database import get_db
from backend.app.models.models import Account, Transaction, AccountFeature, RiskScore, EWSSignal
from backend.app.schemas.schemas import AccountOut, TransactionOut, GraphNetworkOut, GraphNode, GraphEdge

router = APIRouter(prefix="/accounts", tags=["Accounts"])

@router.get("", response_model=List[AccountOut])
def get_accounts(
    risk_level: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(Account)

    if risk_level:
        query = query.filter(Account.current_risk_level == risk_level.upper())
    
    if search:
        query = query.filter(Account.account_id.ilike(f"%{search}%"))

    total = query.count()
    offset = (page - 1) * limit
    accounts = query.order_by(Account.current_risk_score.desc()).offset(offset).limit(limit).all()
    return accounts


@router.get("/{account_id}")
def get_account_detail(account_id: str, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.account_id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    feature = db.query(AccountFeature).filter(AccountFeature.account_id == account_id).first()
    risk_score = db.query(RiskScore).filter(RiskScore.account_id == account_id).order_by(RiskScore.created_at.desc()).first()
    ews_signals = db.query(EWSSignal).filter(EWSSignal.account_id == account_id).all()

    tx_count = db.query(Transaction).filter(
        or_(Transaction.sender_account_id == account_id, Transaction.receiver_account_id == account_id)
    ).count()

    return {
        "account": account,
        "features": feature,
        "risk_summary": risk_score,
        "ews_signals": ews_signals,
        "total_transactions": tx_count
    }


@router.get("/{account_id}/transactions", response_model=List[TransactionOut])
def get_account_transactions(account_id: str, limit: int = 50, db: Session = Depends(get_db)):
    txs = db.query(Transaction).filter(
        or_(Transaction.sender_account_id == account_id, Transaction.receiver_account_id == account_id)
    ).order_by(Transaction.timestamp.desc()).limit(limit).all()
    return txs


@router.get("/{account_id}/risk")
def get_account_risk(account_id: str, db: Session = Depends(get_db)):
    risk_score = db.query(RiskScore).filter(RiskScore.account_id == account_id).order_by(RiskScore.created_at.desc()).first()
    if not risk_score:
        raise HTTPException(status_code=404, detail=f"Risk score for {account_id} not found")
    return risk_score


@router.get("/{account_id}/graph", response_model=GraphNetworkOut)
def get_account_graph(
    account_id: str,
    depth: int = Query(1, ge=1, le=2),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    target_acc = db.query(Account).filter(Account.account_id == account_id).first()
    if not target_acc:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    # Fetch 1-hop or 2-hop connected transactions
    connected_txs = db.query(Transaction).filter(
        or_(Transaction.sender_account_id == account_id, Transaction.receiver_account_id == account_id)
    ).limit(limit).all()

    node_ids = {account_id}
    for tx in connected_txs:
        node_ids.add(tx.sender_account_id)
        node_ids.add(tx.receiver_account_id)

    # Fetch account objects for all node_ids
    accounts_map = {
        a.account_id: a for a in db.query(Account).filter(Account.account_id.in_(list(node_ids))).all()
    }

    nodes = []
    for nid in node_ids:
        acc_obj = accounts_map.get(nid)
        r_score = acc_obj.current_risk_score if acc_obj else 0.0
        r_level = acc_obj.current_risk_level if acc_obj else "LOW"
        a_type = acc_obj.account_type if acc_obj else "SAVINGS"
        nodes.append(GraphNode(
            id=nid,
            label=nid,
            risk_score=r_score,
            risk_level=r_level,
            account_type=a_type
        ))

    # Aggregate edges
    edge_map = {}
    for tx in connected_txs:
        key = (tx.sender_account_id, tx.receiver_account_id)
        if key in edge_map:
            edge_map[key]["amount"] += tx.amount
            edge_map[key]["count"] += 1
        else:
            edge_map[key] = {"amount": tx.amount, "count": 1}

    edges = [
        GraphEdge(source=k[0], target=k[1], amount=v["amount"], count=v["count"])
        for k, v in edge_map.items()
    ]

    return GraphNetworkOut(nodes=nodes, edges=edges)
