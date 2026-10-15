"""
GraphGuard Graph Intelligence Service

Builds an enriched NetworkX graph from the DB, computes graph metrics
(PageRank, betweenness, rings), classifies node roles, joins EWS & alert
data, and returns the EnrichedGraphNetworkOut DTO for the 3D visualizer.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
import networkx as nx
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

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

# These limits only apply to the renderer's investigation subgraph. They never
# change the full transaction graph used by ML, reporting, or analytics.
DEFAULT_MAX_INCOMING_NODES = 10
DEFAULT_MAX_OUTGOING_NODES = 10
EXPANDED_MAX_INCOMING_NODES = 20
EXPANDED_MAX_OUTGOING_NODES = 20
MAX_VISIBLE_NODES = 45
MAX_VISIBLE_EDGES = 44


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
        if src in visible_ids and tgt in visible_ids and src != tgt:
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


def build_investigation_graph(
    db: Session,
    account_id: Optional[str] = None,
    incoming_limit: int = DEFAULT_MAX_INCOMING_NODES,
    outgoing_limit: int = DEFAULT_MAX_OUTGOING_NODES,
    expand: bool = False,
) -> EnrichedGraphNetworkOut:
    """Build a compact, aggregated subgraph for the 3D investigation view.

    The complete transaction graph remains in the database and in the existing
    analytical endpoint. This function deliberately selects only the most
    meaningful direct relationships around one target account for rendering.
    """
    if account_id:
        selected = db.query(Account).filter(Account.account_id == account_id).first()
    else:
        # A useful first view for the dashboard: investigate the highest-risk
        # account rather than drawing a dense global graph.
        selected = (
            db.query(Account)
            .order_by(Account.current_risk_score.desc())
            .first()
        )

    if not selected:
        return EnrichedGraphNetworkOut(nodes=[], edges=[], stats=GraphStats())

    selected_id = selected.account_id
    if expand:
        incoming_limit = max(incoming_limit, EXPANDED_MAX_INCOMING_NODES)
        outgoing_limit = max(outgoing_limit, EXPANDED_MAX_OUTGOING_NODES)
    incoming_limit = min(max(incoming_limit, 1), MAX_VISIBLE_NODES // 2)
    outgoing_limit = min(max(outgoing_limit, 1), MAX_VISIBLE_NODES // 2)

    # Aggregate in SQL before materialising data. Self transactions remain in
    # the analytical data but are intentionally absent from the rendered view.
    relationship_rows = (
        db.query(
            Transaction.sender_account_id.label("source"),
            Transaction.receiver_account_id.label("target"),
            func.sum(Transaction.amount).label("amount"),
            func.count(Transaction.id).label("count"),
            func.min(Transaction.transaction_id).label("tx_id"),
        )
        .filter(
            or_(
                Transaction.sender_account_id == selected_id,
                Transaction.receiver_account_id == selected_id,
            ),
            Transaction.sender_account_id != Transaction.receiver_account_id,
        )
        .group_by(Transaction.sender_account_id, Transaction.receiver_account_id)
        .all()
    )

    total_connected = len({
        row.source if row.target == selected_id else row.target
        for row in relationship_rows
    })
    peer_ids = {
        row.source if row.target == selected_id else row.target
        for row in relationship_rows
    }
    related_accounts = db.query(Account).filter(Account.account_id.in_(peer_ids)).all() if peer_ids else []
    account_map: Dict[str, Account] = {selected_id: selected, **{a.account_id: a for a in related_accounts}}
    feature_rows = (
        db.query(AccountFeature).filter(AccountFeature.account_id.in_(list(account_map))).all()
        if account_map else []
    )
    feature_map = {feature.account_id: feature for feature in feature_rows}
    ews_rows = db.query(EWSSignal).filter(EWSSignal.account_id.in_(list(account_map))).all() if account_map else []
    ews_map: Dict[str, List[EWSSignal]] = {}
    for signal in ews_rows:
        ews_map.setdefault(signal.account_id, []).append(signal)
    alert_rows = (
        db.query(Alert)
        .filter(Alert.account_id.in_(list(account_map)), Alert.status.in_(["NEW", "UNDER_REVIEW", "ESCALATED"]))
        .order_by(Alert.risk_score.desc())
        .all()
        if account_map else []
    )
    alert_map: Dict[str, Alert] = {}
    for alert in alert_rows:
        alert_map.setdefault(alert.account_id, alert)

    max_amount = max((float(row.amount or 0) for row in relationship_rows), default=1.0)
    max_count = max((int(row.count or 0) for row in relationship_rows), default=1)

    def importance(row: Any) -> float:
        peer_id = row.source if row.target == selected_id else row.target
        peer = account_map.get(peer_id)
        risk = float(peer.current_risk_score if peer else 0.0) / 100.0
        suspicious_bonus = 0.25 if peer and (peer.label == 1 or peer.current_risk_level in ("HIGH", "CRITICAL")) else 0.0
        # Volume is primary; frequency and risk make smaller but suspicious
        # relationships discoverable without letting them dominate the view.
        return (float(row.amount or 0) / max_amount) * 0.60 + (int(row.count or 0) / max_count) * 0.20 + risk * 0.20 + suspicious_bonus

    incoming_rows = sorted(
        (row for row in relationship_rows if row.target == selected_id),
        key=importance,
        reverse=True,
    )[:incoming_limit]
    outgoing_rows = sorted(
        (row for row in relationship_rows if row.source == selected_id),
        key=importance,
        reverse=True,
    )[:outgoing_limit]
    selected_rows = (incoming_rows + outgoing_rows)[:MAX_VISIBLE_EDGES]

    # A peer can appear in both directions. Retain both aggregated edges, but
    # give the node one stable semantic type for a clear colour assignment.
    peer_directions: Dict[str, Set[str]] = {}
    peer_importance: Dict[str, float] = {}
    for row in selected_rows:
        peer_id = row.source if row.target == selected_id else row.target
        direction = "incoming" if row.target == selected_id else "outgoing"
        peer_directions.setdefault(peer_id, set()).add(direction)
        peer_importance[peer_id] = max(peer_importance.get(peer_id, 0.0), importance(row))

    # At most a small number of yellow nodes are useful in a directed view.
    # This avoids generated/demo data where many accounts carry alerts from
    # turning every counterpart into the same visual category.
    suspicious_candidates = [
        node_id for node_id in peer_directions
        if (
            (account_map.get(node_id) and (account_map[node_id].current_risk_score >= 80 or account_map[node_id].label == 1))
            or node_id in alert_map
            or node_id in ews_map
        )
    ]
    suspicious_peer_ids = set(sorted(
        suspicious_candidates,
        key=lambda node_id: (
            float(account_map[node_id].current_risk_score if node_id in account_map else 0),
            peer_importance.get(node_id, 0.0),
        ),
        reverse=True,
    )[:3])

    def node_type_for(node_id: str) -> str:
        if node_id == selected_id:
            return "selected"
        account = account_map.get(node_id)
        # Direction is the default semantic cue. Yellow is reserved for the
        # few most important corroborated suspicious neighbours.
        if account and node_id in suspicious_peer_ids:
            return "suspicious"
        directions = peer_directions.get(node_id, set())
        return "incoming" if "incoming" in directions else "outgoing" if "outgoing" in directions else "normal"

    def make_node(node_id: str) -> EnrichedGraphNode:
        account = account_map.get(node_id)
        feature = feature_map.get(node_id)
        signals = ews_map.get(node_id, [])
        alert = alert_map.get(node_id)
        risk_score = float(account.current_risk_score if account else 0.0)
        risk_level = account.current_risk_level if account else "LOW"
        role = "SUSPICIOUS_NEIGHBOUR" if node_type_for(node_id) == "suspicious" else "NORMAL"
        return EnrichedGraphNode(
            id=node_id,
            label=node_id,
            risk_score=round(risk_score, 1),
            risk_level=risk_level,
            account_type=account.account_type if account else "SAVINGS",
            role=role,
            ews_codes=[signal.signal_code for signal in signals],
            ews_types=[signal.signal_type for signal in signals],
            ews_count=len(signals),
            alert_id=alert.alert_id if alert else None,
            alert_severity=alert.severity if alert else None,
            incoming_count=int(feature.incoming_count or 0) if feature else 0,
            outgoing_count=int(feature.outgoing_count or 0) if feature else 0,
            incoming_total=round(float(feature.incoming_total or 0), 2) if feature else 0.0,
            outgoing_total=round(float(feature.outgoing_total or 0), 2) if feature else 0.0,
            in_degree=int(feature.in_degree or 0) if feature else 0,
            out_degree=int(feature.out_degree or 0) if feature else 0,
            risky_neighbor_ratio=round(float(feature.risky_neighbor_ratio or 0), 4) if feature else 0.0,
            is_fraud=bool(account and account.label == 1),
            node_type=node_type_for(node_id),
        )

    ordered_peer_ids = sorted(peer_directions, key=lambda nid: peer_importance[nid], reverse=True)
    nodes = [make_node(selected_id)] + [make_node(node_id) for node_id in ordered_peer_ids]
    edges = [
        EnrichedGraphEdge(
            source=row.source,
            target=row.target,
            amount=round(float(row.amount or 0), 2),
            count=int(row.count or 0),
            tx_id=row.tx_id,
            direction="incoming" if row.target == selected_id else "outgoing",
        )
        for row in selected_rows
    ]
    suspicious_count = sum(1 for node in nodes if node.node_type == "suspicious")
    stats = GraphStats(
        total_nodes=len(nodes),
        fraud_nodes=sum(1 for node in nodes if node.is_fraud or node.risk_level in ("HIGH", "CRITICAL")),
        total_edges=len(edges),
        critical_nodes=sum(1 for node in nodes if node.risk_level == "CRITICAL"),
        high_nodes=sum(1 for node in nodes if node.risk_level == "HIGH"),
        selected_account=selected_id,
        visible_nodes=len(nodes),
        incoming_count=len(incoming_rows),
        outgoing_count=len(outgoing_rows),
        suspicious_count=suspicious_count,
        visible_edges=len(edges),
        total_connected=total_connected,
        is_expanded=expand,
    )
    return EnrichedGraphNetworkOut(nodes=nodes, edges=edges, stats=stats)
