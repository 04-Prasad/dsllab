"""
GraphGuard SQLAlchemy ORM Data Models
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(50), unique=True, index=True, nullable=False)
    account_created_at = Column(String(50), nullable=True)
    account_type = Column(String(50), default="SAVINGS")
    status = Column(String(20), default="ACTIVE")
    label = Column(Integer, default=0)
    
    current_risk_score = Column(Float, default=0.0)
    current_risk_level = Column(String(20), default="LOW")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(50), unique=True, index=True, nullable=False)

    sender_account_id = Column(String(50), index=True, nullable=False)
    receiver_account_id = Column(String(50), index=True, nullable=False)

    amount = Column(Float, nullable=False)
    timestamp = Column(String(50), index=True, nullable=False)

    transaction_type = Column(String(50), default="TRANSFER")
    channel = Column(String(50), default="MOBILE_APP")
    status = Column(String(20), default="SUCCESS")
    label = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)


class AccountFeature(Base):
    __tablename__ = "account_features"

    account_id = Column(String(50), primary_key=True, index=True)
    
    incoming_count = Column(Integer, default=0)
    outgoing_count = Column(Integer, default=0)

    incoming_total = Column(Float, default=0.0)
    outgoing_total = Column(Float, default=0.0)

    unique_senders = Column(Integer, default=0)
    unique_receivers = Column(Integer, default=0)

    velocity_1h = Column(Integer, default=0)
    velocity_24h = Column(Integer, default=0)

    dormancy_days = Column(Float, default=0.0)

    in_degree = Column(Integer, default=0)
    out_degree = Column(Integer, default=0)

    risky_neighbor_ratio = Column(Float, default=0.0)
    
    generated_at = Column(DateTime, default=datetime.utcnow)


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(50), index=True, nullable=False)

    ml_score = Column(Float, default=0.0)
    ews_score = Column(Float, default=0.0)
    graph_score = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)

    risk_level = Column(String(20), default="LOW")
    reasons = Column(JSON, nullable=True)
    model_version = Column(String(50), default="graphsage-v1")

    created_at = Column(DateTime, default=datetime.utcnow)


class EWSSignal(Base):
    __tablename__ = "ews_signals"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String(50), index=True, nullable=False)

    signal_code = Column(String(20), nullable=False)
    signal_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="HIGH")

    description = Column(Text, nullable=True)
    observed_value = Column(String(100), nullable=True)
    threshold_value = Column(String(100), nullable=True)

    evidence = Column(JSON, nullable=True)
    triggered_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(50), unique=True, index=True, nullable=False)
    account_id = Column(String(50), index=True, nullable=False)

    severity = Column(String(20), default="HIGH")
    risk_score = Column(Float, default=0.0)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String(30), default="NEW") # NEW, UNDER_REVIEW, ESCALATED, RESOLVED, FALSE_POSITIVE

    created_at = Column(DateTime, default=datetime.utcnow)
