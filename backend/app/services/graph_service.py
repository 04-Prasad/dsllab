"""
GraphGuard Graph Intelligence Service

Builds an enriched NetworkX graph from the DB, computes graph metrics
(PageRank, betweenness, rings), classifies node roles, joins EWS & alert
data, and returns the EnrichedGraphNetworkOut DTO for the 3D visualizer.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
import networkx as nx
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.models.models import Account, Transaction, AccountFeature, EWSSignal, Alert
from backend.app.schemas.schemas import (
    EnrichedGraphNode, EnrichedGraphEdge, GraphStats, EnrichedGraphNetworkOut
)


# ── Thresholds for role classification ─────────────────────────────────────────

ROLE_THRESHOLDS = {
    "hub_in_degree": 10,
    "hub_pagerank": 0.005,
    "bridge_betweenness": 0.02,
    "mule_rapid_ratio": 0.80,
    "suspicious_neighbour_ratio": 0.35,
}


def _classify_role(
    account_id: str,
    in_degree: int,
    out_degree: int,
    pagerank: float,
    betweenness: float,
    ring_members: Set[str],
    feature_map: Dict[str, Any],
) -> str:
    """Return a role string for this account based on graph metrics."""
    if account_id in ring_members:
        return "RING_MEMBER"

    if pagerank >= ROLE_THRESHOLDS["hub_pagerank"] or in_degree >= ROLE_THRESHOLDS["hub_in_degree"]:
        return "HUB"

    if betweenness >= ROLE_THRESHOLDS["bridge_betweenness"]:
        return "BRIDGE"

    feat = feature_map.get(account_id)
    if feat:
        rapid = feat.get("rapid_movement_ratio", 0.0)
        if rapid >= ROLE_THRESHOLDS["mule_rapid_ratio"]:
            return "MULE"
        rn_ratio = feat.get("risky_neighbor_ratio", 0.0)
        if rn_ratio >= ROLE_THRESHOLDS["suspicious_neighbour_ratio"]:
            return "SUSPICIOUS_NEIGHBOUR"

    return "NORMAL"


def build_enriched_graph(
    db: Session,
    limit: int = 200,
    risk_threshold: float = 0.0,
    fraud_only: bool = False,
    ring_members_only: bool = False,
    account_id: Optional[str] = None,
) -> EnrichedGraphNetworkOut:
    """
    Build the full enriched graph for the 3D visualizer.

    Steps:
      1. Load accounts (optionally centred on account_id)
      2. Load their transactions to form edges
      3. Build NetworkX DiGraph
      4. Compute PageRank + betweenness centrality
      5. Detect rings (cycles ≤ 6 nodes)
      6. Classify node roles
      7. Join EWS signals + alerts per account
      8. Apply filters (risk_threshold, fraud_only, ring_members_only)
      9. Return EnrichedGraphNetworkOut
    """

    # ── 1. Determine account set ─────────────────────────────────────────────
    if account_id:
        center_acc = db.query(Account).filter(Account.account_id == account_id).first()
        if not center_acc:
            return EnrichedGraphNetworkOut(nodes=[], edges=[], stats=GraphStats())

        # Load transactions involving this account (1-hop neighbourhood)
        txs = db.query(Transaction).filter(
            or_(
                Transaction.sender_account_id == account_id,
                Transaction.receiver_account_id == account_id,
            )
        ).limit(limit).all()

        # Collect neighbour IDs and load more of their transactions for depth
        hop1_ids = {account_id}
        for tx in txs:
            hop1_ids.add(tx.sender_account_id)
            hop1_ids.add(tx.receiver_account_id)

        # Extend with transactions between neighbours (limited)
        extra_txs = db.query(Transaction).filter(
            or_(
                Transaction.sender_account_id.in_(hop1_ids),
                Transaction.receiver_account_id.in_(hop1_ids),
            )
        ).limit(limit * 2).all()

        all_txs = {t.id: t for t in txs + extra_txs}
        txs = list(all_txs.values())

    else:
        # Global view: load high-risk accounts first, then fill with others
        high_risk_accs = (
            db.query(Account)
            .filter(Account.current_risk_level.in_(["HIGH", "CRITICAL"]))
            .order_by(Account.current_risk_score.desc())
            .limit(min(limit // 2, 80))
            .all()
        )
        seed_ids = [a.account_id for a in high_risk_accs]

        if not seed_ids:
            seed_ids = [
                a.account_id
                for a in db.query(Account)
                .order_by(Account.current_risk_score.desc())
                .limit(20)
                .all()
            ]

        txs = db.query(Transaction).filter(
            or_(
                Transaction.sender_account_id.in_(seed_ids),
                Transaction.receiver_account_id.in_(seed_ids),
            )
        ).limit(limit * 2).all()

    # ── 2. Collect all node IDs ──────────────────────────────────────────────
    node_ids: Set[str] = set()
    for tx in txs:
        node_ids.add(tx.sender_account_id)
        node_ids.add(tx.receiver_account_id)
    if account_id:
        node_ids.add(account_id)

    # ── 3. Load account objects ──────────────────────────────────────────────
    acc_records = db.query(Account).filter(Account.account_id.in_(list(node_ids))).all()
    acc_map: Dict[str, Account] = {a.account_id: a for a in acc_records}

    # ── 4. Load AccountFeature rows ──────────────────────────────────────────
    feat_rows = db.query(AccountFeature).filter(AccountFeature.account_id.in_(list(node_ids))).all()
    feature_map: Dict[str, Dict[str, Any]] = {}
    for f in feat_rows:
        feature_map[f.account_id] = {
            "incoming_count": f.incoming_count or 0,
            "outgoing_count": f.outgoing_count or 0,
            "incoming_total": f.incoming_total or 0.0,
            "outgoing_total": f.outgoing_total or 0.0,
            "in_degree": f.in_degree or 0,
            "out_degree": f.out_degree or 0,
            "rapid_movement_ratio": (f.outgoing_total / f.incoming_total)
                if (f.incoming_total and f.incoming_total > 0) else 0.0,
            "risky_neighbor_ratio": f.risky_neighbor_ratio or 0.0,
        }

    # ── 5. Build NetworkX DiGraph ────────────────────────────────────────────
    G = nx.DiGraph()
    for nid in node_ids:
        G.add_node(nid)

    # Build edge aggregation map {(src, tgt): {amount, count, tx_id}}
    edge_agg: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for tx in txs:
        key = (tx.sender_account_id, tx.receiver_account_id)
        if key in edge_agg:
            edge_agg[key]["amount"] += tx.amount
            edge_agg[key]["count"] += 1
        else:
            edge_agg[key] = {"amount": tx.amount, "count": 1, "tx_id": tx.transaction_id}
        G.add_edge(tx.sender_account_id, tx.receiver_account_id, weight=tx.amount)

    # ── 6. Compute graph metrics ─────────────────────────────────────────────
    try:
        pagerank: Dict[str, float] = nx.pagerank(G, alpha=0.85, max_iter=100)
    except Exception:
        pagerank = {nid: 0.0 for nid in node_ids}

    try:
        # Use undirected for betweenness (faster and directionally agnostic)
        G_undirected = G.to_undirected()
        betweenness: Dict[str, float] = nx.betweenness_centrality(
            G_undirected, normalized=True, k=min(50, len(G_undirected))
        )
    except Exception:
        betweenness = {nid: 0.0 for nid in node_ids}

    # ── 7. Detect rings (simple cycles ≤ 6 nodes) ────────────────────────────
    ring_members: Set[str] = set()
    ring_count = 0
    ring_id_map: Dict[str, str] = {}

    try:
        cycle_gen = nx.simple_cycles(G)
        for cycle in cycle_gen:
            if 3 <= len(cycle) <= 6:
                ring_count += 1
                ring_label = f"RING-{ring_count:03d}"
                for node in cycle:
                    ring_members.add(node)
                    if node not in ring_id_map:
                        ring_id_map[node] = ring_label
                if ring_count >= 20:   # cap detection to avoid runaway
                    break
    except Exception:
        pass

    # ── 8. Load EWS signals ──────────────────────────────────────────────────
    ews_rows = db.query(EWSSignal).filter(EWSSignal.account_id.in_(list(node_ids))).all()
    ews_map: Dict[str, List[EWSSignal]] = {}
    for ews in ews_rows:
        ews_map.setdefault(ews.account_id, []).append(ews)

    # ── 9. Load active alerts ────────────────────────────────────────────────
    alert_rows = (
        db.query(Alert)
        .filter(Alert.account_id.in_(list(node_ids)))
        .filter(Alert.status.in_(["NEW", "UNDER_REVIEW", "ESCALATED"]))
        .order_by(Alert.risk_score.desc())
        .all()
    )
    alert_map: Dict[str, Alert] = {}
    for alert in alert_rows:
        if alert.account_id not in alert_map:
            alert_map[alert.account_id] = alert

    # ── 10. Assemble enriched nodes ──────────────────────────────────────────
    enriched_nodes: List[EnrichedGraphNode] = []
    for nid in node_ids:
        acc = acc_map.get(nid)
        r_score = acc.current_risk_score if acc else 0.0
        r_level = acc.current_risk_level if acc else "LOW"
        a_type = acc.account_type if acc else "SAVINGS"
        is_fraud = bool(acc and acc.label == 1)

        # Apply pre-filter
        if r_score < risk_threshold:
            continue
        if fraud_only and not is_fraud and r_level not in ("HIGH", "CRITICAL"):
            continue

        feat = feature_map.get(nid, {})
        pg = pagerank.get(nid, 0.0)
        bw = betweenness.get(nid, 0.0)
        in_deg = G.in_degree(nid)
        out_deg = G.out_degree(nid)

        role = _classify_role(nid, in_deg, out_deg, pg, bw, ring_members, feature_map)

        if ring_members_only and role != "RING_MEMBER":
            continue

        ews_signals = ews_map.get(nid, [])
        ews_codes = [s.signal_code for s in ews_signals]
        ews_types = [s.signal_type for s in ews_signals]

        active_alert = alert_map.get(nid)

        enriched_nodes.append(
            EnrichedGraphNode(
                id=nid,
                label=nid,
                risk_score=round(r_score, 1),
                risk_level=r_level,
                account_type=a_type,
                role=role,
                ring_id=ring_id_map.get(nid),
                ews_codes=ews_codes,
                ews_types=ews_types,
                ews_count=len(ews_signals),
                alert_id=active_alert.alert_id if active_alert else None,
                alert_severity=active_alert.severity if active_alert else None,
                incoming_count=feat.get("incoming_count", 0),
                outgoing_count=feat.get("outgoing_count", 0),
                incoming_total=round(feat.get("incoming_total", 0.0), 2),
                outgoing_total=round(feat.get("outgoing_total", 0.0), 2),
                pagerank=round(pg, 6),
                in_degree=in_deg,
                out_degree=out_deg,
                betweenness=round(bw, 6),
                risky_neighbor_ratio=round(feat.get("risky_neighbor_ratio", 0.0), 4),
                is_fraud=is_fraud,
            )
        )

    # ── 11. Assemble enriched edges (only for included nodes) ────────────────
    visible_ids = {n.id for n in enriched_nodes}
    enriched_edges: List[EnrichedGraphEdge] = []
    for (src, tgt), agg in edge_agg.items():
        if src in visible_ids and tgt in visible_ids:
            enriched_edges.append(
                EnrichedGraphEdge(
                    source=src,
                    target=tgt,
                    amount=round(agg["amount"], 2),
                    count=agg["count"],
                    tx_id=agg.get("tx_id"),
                )
            )

    # ── 12. Compute stats ────────────────────────────────────────────────────
    fraud_count = sum(1 for n in enriched_nodes if n.is_fraud or n.risk_level in ("HIGH", "CRITICAL"))
    critical_count = sum(1 for n in enriched_nodes if n.risk_level == "CRITICAL")
    high_count = sum(1 for n in enriched_nodes if n.risk_level == "HIGH")
    visible_rings = len({n.ring_id for n in enriched_nodes if n.ring_id})

    stats = GraphStats(
        total_nodes=len(enriched_nodes),
        fraud_nodes=fraud_count,
        total_edges=len(enriched_edges),
        rings=visible_rings,
        critical_nodes=critical_count,
        high_nodes=high_count,
    )

    return EnrichedGraphNetworkOut(
        nodes=enriched_nodes,
        edges=enriched_edges,
        stats=stats,
    )
