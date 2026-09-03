"""
GraphGuard Pydantic Schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class AccountBase(BaseModel):
    account_id: str
    account_created_at: Optional[str] = None
    account_type: str = "SAVINGS"
    status: str = "ACTIVE"
    current_risk_score: float = 0.0
    current_risk_level: str = "LOW"

class AccountOut(AccountBase):
    id: int
    label: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TransactionOut(BaseModel):
    id: int
    transaction_id: str
    sender_account_id: str
    receiver_account_id: str
    amount: float
    timestamp: str
    transaction_type: str
    channel: str
    status: str
    label: int = 0

    class Config:
        from_attributes = True

class AlertOut(BaseModel):
    id: int
    alert_id: str
    account_id: str
    severity: str
    risk_score: float
    title: str
    description: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AlertStatusUpdate(BaseModel):
    status: str # NEW, UNDER_REVIEW, ESCALATED, RESOLVED, FALSE_POSITIVE

class EWSSignalOut(BaseModel):
    id: int
    account_id: str
    signal_code: str
    signal_type: str
    severity: str
    description: Optional[str] = None
    observed_value: Optional[str] = None
    threshold_value: Optional[str] = None
    evidence: Optional[Any] = None
    triggered_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DashboardSummaryOut(BaseModel):
    total_accounts: int
    total_transactions: int
    active_alerts: int
    high_risk_accounts: int
    critical_accounts: int
    ews_count: int
    risk_distribution: Dict[str, int]
    top_risk_accounts: List[Dict[str, Any]]
    recent_alerts: List[AlertOut]

class GraphNode(BaseModel):
    id: str
    label: str
    risk_score: float
    risk_level: str
    account_type: str

class GraphEdge(BaseModel):
    source: str
    target: str
    amount: float
    count: int

class GraphNetworkOut(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# ── Enriched 3D Network Graph schemas ──────────────────────────────────────────

class EnrichedGraphNode(BaseModel):
    id: str
    label: str
    risk_score: float
    risk_level: str
    account_type: str
    # Graph role classification
    role: str = "NORMAL"          # HUB / BRIDGE / MULE / RING_MEMBER / SUSPICIOUS_NEIGHBOUR / NORMAL
    ring_id: Optional[str] = None
    # EWS signals
    ews_codes: List[str] = []     # ["EWS-002", "EWS-005"]
    ews_types: List[str] = []     # ["FAN_IN_SPIKE", "RAPID_FUND_MOVEMENT"]
    ews_count: int = 0
    # Active alert
    alert_id: Optional[str] = None
    alert_severity: Optional[str] = None
    # Transaction features
    incoming_count: int = 0
    outgoing_count: int = 0
    incoming_total: float = 0.0
    outgoing_total: float = 0.0
    # Graph centrality metrics
    pagerank: float = 0.0
    in_degree: int = 0
    out_degree: int = 0
    betweenness: float = 0.0
    risky_neighbor_ratio: float = 0.0
    # Fraud label
    is_fraud: bool = False


class EnrichedGraphEdge(BaseModel):
    source: str
    target: str
    amount: float
    count: int
    tx_id: Optional[str] = None   # representative transaction ID


class GraphStats(BaseModel):
    total_nodes: int = 0
    fraud_nodes: int = 0
    total_edges: int = 0
    rings: int = 0
    critical_nodes: int = 0
    high_nodes: int = 0


class EnrichedGraphNetworkOut(BaseModel):
    nodes: List[EnrichedGraphNode]
    edges: List[EnrichedGraphEdge]
    stats: GraphStats
