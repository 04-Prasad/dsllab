"""
GraphGuard Deterministic Early Warning Signal (EWS) Engine
Evaluates account behavioral and graph features against configurable fraud risk thresholds.
"""

from typing import Dict, List, Any

# Demo default configuration
EWS_CONFIG = {
    "velocity_1h_threshold": 15,
    "fan_in_senders_threshold": 10,
    "fan_out_receivers_threshold": 10,
    "dormancy_days_threshold": 30,
    "dormancy_burst_txs": 5,
    "rapid_movement_min_amount": 50000.0,
    "rapid_movement_ratio_threshold": 0.80,
    "risky_neighbor_ratio_threshold": 0.35,
    "risky_neighbor_count_threshold": 2,
}

EWS_WEIGHTS = {
    "EWS-001": 20, # Velocity Spike
    "EWS-002": 25, # Fan-In Spike
    "EWS-003": 20, # Fan-Out Spike
    "EWS-004": 25, # Dormancy Burst
    "EWS-005": 30, # Rapid Movement
    "EWS-006": 20, # High Risk Neighborhood
    "EWS-007": 30, # Circular Flow
}

def evaluate_account_ews(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates an account's feature dict and returns triggered EWS signals, EWS score (0-100), and explanations.
    """
    triggered_signals = []
    reasons = []

    # EWS-001: Velocity Spike
    vel_1h = features.get("transaction_velocity_1h", 0)
    if vel_1h >= EWS_CONFIG["velocity_1h_threshold"]:
        triggered_signals.append({
            "code": "EWS-001",
            "type": "VELOCITY_SPIKE",
            "severity": "HIGH",
            "description": f"High transaction velocity detected: {vel_1h} transactions in 1 hour (Threshold: {EWS_CONFIG['velocity_1h_threshold']})",
            "observed": vel_1h,
            "threshold": EWS_CONFIG["velocity_1h_threshold"]
        })
        reasons.append(f"High transaction velocity detected ({vel_1h} txns/hr)")

    # EWS-002: Fan-In Spike
    senders = features.get("unique_senders", 0)
    if senders >= EWS_CONFIG["fan_in_senders_threshold"]:
        triggered_signals.append({
            "code": "EWS-002",
            "type": "FAN_IN_SPIKE",
            "severity": "CRITICAL",
            "description": f"Multiple incoming sources detected: {senders} unique incoming senders (Threshold: {EWS_CONFIG['fan_in_senders_threshold']})",
            "observed": senders,
            "threshold": EWS_CONFIG["fan_in_senders_threshold"]
        })
        reasons.append(f"{senders} unique incoming counterparty accounts detected in peak window")

    # EWS-003: Fan-Out Spike
    receivers = features.get("unique_receivers", 0)
    if receivers >= EWS_CONFIG["fan_out_receivers_threshold"]:
        triggered_signals.append({
            "code": "EWS-003",
            "type": "FAN_OUT_SPIKE",
            "severity": "HIGH",
            "description": f"Rapid dispersion detected: {receivers} unique outgoing receiver accounts (Threshold: {EWS_CONFIG['fan_out_receivers_threshold']})",
            "observed": receivers,
            "threshold": EWS_CONFIG["fan_out_receivers_threshold"]
        })
        reasons.append(f"{receivers} unique outgoing destination accounts detected in peak window")

    # EWS-004: Dormancy Burst
    dormancy = features.get("dormancy_days", 0.0)
    if dormancy >= EWS_CONFIG["dormancy_days_threshold"] and vel_1h >= EWS_CONFIG["dormancy_burst_txs"]:
        triggered_signals.append({
            "code": "EWS-004",
            "type": "DORMANCY_BURST",
            "severity": "CRITICAL",
            "description": f"Account active after {dormancy:.1f} days of dormancy with sudden spike of {vel_1h} transactions",
            "observed": f"{dormancy:.1f} days / {vel_1h} txs",
            "threshold": f"{EWS_CONFIG['dormancy_days_threshold']} days / {EWS_CONFIG['dormancy_burst_txs']} txs"
        })
        reasons.append(f"Sudden activity burst ({vel_1h} txns) following {dormancy:.1f} days of dormancy")

    # EWS-005: Rapid Fund Movement
    inc_amt = features.get("incoming_amount_total", 0.0)
    rapid_ratio = features.get("rapid_movement_ratio", 0.0)
    if inc_amt >= EWS_CONFIG["rapid_movement_min_amount"] and rapid_ratio >= EWS_CONFIG["rapid_movement_ratio_threshold"]:
        triggered_signals.append({
            "code": "EWS-005",
            "type": "RAPID_FUND_MOVEMENT",
            "severity": "CRITICAL",
            "description": f"Received ₹{inc_amt:,.2f} and immediately transferred out {int(rapid_ratio * 100)}% of funds",
            "observed": f"{int(rapid_ratio * 100)}%",
            "threshold": f"{int(EWS_CONFIG['rapid_movement_ratio_threshold'] * 100)}%"
        })
        reasons.append(f"Transferred out {int(rapid_ratio * 100)}% of incoming funds shortly after receipt")

    # EWS-006: High Risk Neighborhood
    rn_ratio = features.get("risky_neighbor_ratio", 0.0)
    rn_count = features.get("risky_neighbor_count", 0)
    if rn_ratio >= EWS_CONFIG["risky_neighbor_ratio_threshold"] or rn_count >= EWS_CONFIG["risky_neighbor_count_threshold"]:
        triggered_signals.append({
            "code": "EWS-006",
            "type": "HIGH_RISK_NEIGHBOURHOOD",
            "severity": "HIGH",
            "description": f"Connected to {rn_count} suspicious accounts ({int(rn_ratio * 100)}% of counterparties)",
            "observed": f"{rn_count} nodes ({int(rn_ratio * 100)}%)",
            "threshold": f"{EWS_CONFIG['risky_neighbor_count_threshold']} nodes / {int(EWS_CONFIG['risky_neighbor_ratio_threshold'] * 100)}%"
        })
        reasons.append(f"{rn_count} connected counterparty accounts are flagged as suspicious")

    # EWS-007: Circular Flow
    circ_ind = features.get("circular_flow_indicator", 0)
    if circ_ind == 1:
        triggered_signals.append({
            "code": "EWS-007",
            "type": "CIRCULAR_FLOW",
            "severity": "CRITICAL",
            "description": "Closed circular transaction pattern detected (A -> B -> C -> A)",
            "observed": "Cycle Present",
            "threshold": "None"
        })
        reasons.append("Participates in a closed-loop circular money flow network")

    # Calculate raw EWS score sum
    raw_ews_score = sum(EWS_WEIGHTS.get(sig["code"], 10) for sig in triggered_signals)
    normalized_ews_score = min(100.0, float(raw_ews_score))

    return {
        "ews_score": round(normalized_ews_score, 1),
        "triggered_signals": triggered_signals,
        "reasons": reasons
    }
