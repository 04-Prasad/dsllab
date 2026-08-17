"""
GraphGuard Dashboard API Routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.database import get_db
from backend.app.models.models import Account, Transaction, Alert, EWSSignal
from backend.app.schemas.schemas import DashboardSummaryOut, AlertOut

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummaryOut)
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_accounts = db.query(func.count(Account.id)).scalar() or 0
    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    active_alerts = db.query(func.count(Alert.id)).filter(Alert.status.in_(["NEW", "UNDER_REVIEW", "ESCALATED"])).scalar() or 0
    
    high_risk_accounts = db.query(func.count(Account.id)).filter(Account.current_risk_level == "HIGH").scalar() or 0
    critical_accounts = db.query(func.count(Account.id)).filter(Account.current_risk_level == "CRITICAL").scalar() or 0
    ews_count = db.query(func.count(EWSSignal.id)).scalar() or 0

    low_count = db.query(func.count(Account.id)).filter(Account.current_risk_level == "LOW").scalar() or 0
    medium_count = db.query(func.count(Account.id)).filter(Account.current_risk_level == "MEDIUM").scalar() or 0

    risk_distribution = {
        "LOW": low_count,
        "MEDIUM": medium_count,
        "HIGH": high_risk_accounts,
        "CRITICAL": critical_accounts
    }

    top_accs = db.query(Account).order_by(Account.current_risk_score.desc()).limit(5).all()
    top_risk_accounts = [
        {
            "account_id": a.account_id,
            "risk_score": a.current_risk_score,
            "risk_level": a.current_risk_level,
            "account_type": a.account_type
        }
        for a in top_accs
    ]

    recent_alerts_orm = db.query(Alert).order_by(Alert.created_at.desc()).limit(5).all()

    return {
        "total_accounts": total_accounts,
        "total_transactions": total_transactions,
        "active_alerts": active_alerts,
        "high_risk_accounts": high_risk_accounts,
        "critical_accounts": critical_accounts,
        "ews_count": ews_count,
        "risk_distribution": risk_distribution,
        "top_risk_accounts": top_risk_accounts,
        "recent_alerts": recent_alerts_orm
    }
