"""
GraphGuard Alerts API Routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.models.models import Alert, User
from backend.app.schemas.schemas import AlertOut, AlertStatusUpdate
from backend.app.api.deps import RoleChecker

all_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST"])
investigators_admins = RoleChecker(["ADMIN", "INVESTIGATOR"])

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("", response_model=List[AlertOut])
def get_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    query = db.query(Alert)
    if status:
        query = query.filter(Alert.status == status.upper())
    if severity:
        query = query.filter(Alert.severity == severity.upper())

    offset = (page - 1) * limit
    return query.order_by(Alert.risk_score.desc(), Alert.created_at.desc()).offset(offset).limit(limit).all()

@router.get("/{alert_id}", response_model=AlertOut)
def get_alert_detail(
    alert_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(all_roles)
):
    alert = db.query(Alert).filter((Alert.alert_id == alert_id) | (Alert.id == int(alert_id) if alert_id.isdigit() else False)).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alert

@router.patch("/{alert_id}", response_model=AlertOut)
def update_alert_status(
    alert_id: str, 
    payload: AlertStatusUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(investigators_admins)
):
    alert = db.query(Alert).filter((Alert.alert_id == alert_id) | (Alert.id == int(alert_id) if alert_id.isdigit() else False)).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    
    valid_statuses = ["NEW", "UNDER_REVIEW", "ESCALATED", "RESOLVED", "FALSE_POSITIVE"]
    new_status = payload.status.upper()
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    alert.status = new_status
    db.commit()
    db.refresh(alert)
    return alert
