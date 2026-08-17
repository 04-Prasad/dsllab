"""
GraphGuard Global Graph API Routes
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.db.database import get_db
from backend.app.models.models import Account, Transaction
from backend.app.schemas.schemas import GraphNetworkOut, GraphNode, GraphEdge

router = APIRouter(prefix="/graph", tags=["Graph"])

@router.get("/search", response_model=GraphNetworkOut)
def search_graph(
    account_id: Optional[str] = Query(None, description="Account ID to center the graph around"),
    risk_level: Optional[str] = Query(None, description="Filter nodes by minimum risk level"),
    limit: int = Query(60, ge=10, le=200),
    db: Session = Depends(get_db)
):
    """
    Returns graph nodes and transaction edges centered around an account or high-risk accounts.
    """
    if account_id:
        center_acc = db.query(Account).filter(Account.account_id == account_id).first()
        if not center_acc:
            raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

        txs = db.query(Transaction).filter(
            or_(Transaction.sender_account_id == account_id, Transaction.receiver_account_id == account_id)
        ).limit(limit).all()
    else:
        # Default view: top high-risk / critical accounts
        acc_query = db.query(Account)
        if risk_level:
            acc_query = acc_query.filter(Account.current_risk_level == risk_level.upper())
        else:
            acc_query = acc_query.filter(Account.current_risk_level.in_(["HIGH", "CRITICAL"]))
        
        target_accs = [a.account_id for a in acc_query.limit(15).all()]
        if not target_accs:
            target_accs = [a.account_id for a in db.query(Account).order_by(Account.current_risk_score.desc()).limit(10).all()]

        txs = db.query(Transaction).filter(
            or_(Transaction.sender_account_id.in_(target_accs), Transaction.receiver_account_id.in_(target_accs))
        ).limit(limit).all()

    node_ids = set()
    for tx in txs:
        node_ids.add(tx.sender_account_id)
        node_ids.add(tx.receiver_account_id)

    if account_id:
        node_ids.add(account_id)

    acc_records = db.query(Account).filter(Account.account_id.in_(list(node_ids))).all()
    acc_map = {a.account_id: a for a in acc_records}

    nodes = []
    for nid in node_ids:
        acc_obj = acc_map.get(nid)
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

    edge_map = {}
    for tx in txs:
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
