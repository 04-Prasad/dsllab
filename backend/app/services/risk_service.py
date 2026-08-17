"""
GraphGuard Risk Fusion Engine
Combines GNN machine learning probabilities, EWS rule scores, and graph context signals.
"""

from typing import Dict, List, Any

# Configurable Risk Weights
DEFAULT_RISK_WEIGHTS = {
    "ml_weight": 0.50,
    "ews_weight": 0.35,
    "graph_weight": 0.15,
}

FALLBACK_RISK_WEIGHTS = {
    "ews_weight": 0.70,
    "graph_weight": 0.30,
}

def classify_risk_level(score: float) -> str:
    if score >= 80.0:
        return "CRITICAL"
    elif score >= 60.0:
        return "HIGH"
    elif score >= 30.0:
        return "MEDIUM"
    else:
        return "LOW"

def calculate_risk_fusion(
    account_id: str,
    ml_prob: float,
    ews_result: Dict[str, Any],
    features: Dict[str, Any],
    ml_enabled: bool = True
) -> Dict[str, Any]:
    """
    Computes final risk score (0-100), risk level, and human-readable explanations.
    """
    ews_score = ews_result.get("ews_score", 0.0)
    triggered_signals = ews_result.get("triggered_signals", [])
    reasons = list(ews_result.get("reasons", []))

    # Compute Graph Context Score (0-100)
    rn_ratio = features.get("risky_neighbor_ratio", 0.0)
    rn_count = features.get("risky_neighbor_count", 0)
    circ_ind = features.get("circular_flow_indicator", 0)
    pagerank = features.get("pagerank", 0.0)

    raw_graph_score = (rn_ratio * 50.0) + (min(rn_count, 5) * 10.0) + (circ_ind * 30.0) + (min(pagerank * 1000, 20.0))
    graph_context_score = min(100.0, float(raw_graph_score))

    if rn_count > 0 and f"{rn_count} connected counterparty accounts are flagged as suspicious" not in reasons:
        reasons.append(f"{rn_count} connected counterparty accounts flagged in graph neighborhood")

    ml_score_100 = round(ml_prob * 100.0, 1)

    if ml_enabled:
        final_score = (
            (DEFAULT_RISK_WEIGHTS["ml_weight"] * ml_score_100) +
            (DEFAULT_RISK_WEIGHTS["ews_weight"] * ews_score) +
            (DEFAULT_RISK_WEIGHTS["graph_weight"] * graph_context_score)
        )
        if ml_prob >= 0.75:
            reasons.append(f"GNN GraphSAGE model detected high anomaly pattern probability ({int(ml_prob * 100)}%)")
    else:
        final_score = (
            (FALLBACK_RISK_WEIGHTS["ews_weight"] * ews_score) +
            (FALLBACK_RISK_WEIGHTS["graph_weight"] * graph_context_score)
        )

    final_score = round(min(100.0, max(0.0, float(final_score))), 1)
    risk_level = classify_risk_level(final_score)

    if len(reasons) == 0:
        reasons.append("Account behavior matches normal expected transaction patterns")

    evidence = {
        "unique_senders": features.get("unique_senders", 0),
        "unique_receivers": features.get("unique_receivers", 0),
        "velocity_1h": features.get("transaction_velocity_1h", 0),
        "dormancy_days": features.get("dormancy_days", 0.0),
        "rapid_movement_ratio": features.get("rapid_movement_ratio", 0.0),
        "risky_neighbors": rn_count,
        "circular_flow": circ_ind
    }

    return {
        "account_id": str(account_id),
        "risk_score": final_score,
        "risk_level": risk_level,
        "ml_score": ml_score_100,
        "ews_score": ews_score,
        "graph_context_score": round(graph_context_score, 1),
        "triggered_ews": [s["type"] for s in triggered_signals],
        "ews_signals_detail": triggered_signals,
        "reasons": reasons,
        "evidence": evidence
    }
