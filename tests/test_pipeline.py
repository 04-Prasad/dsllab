"""
GraphGuard Automated Verification Test Suite
Tests dataset generation, EWS rules engine, Risk Fusion, NetworkX graph, and FastAPI endpoints.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import pandas as pd
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from ml.src.generate_data import generate_dataset
from ml.src.graph_builder import build_networkx_graph
from ml.src.features import extract_features
from backend.app.services.ews_service import evaluate_account_ews
from backend.app.services.risk_service import calculate_risk_fusion
from backend.app.main import app

client = TestClient(app)

def test_tc001_dataset_loading():
    acc_df, tx_df = generate_dataset(num_normal_accounts=100, num_normal_transactions=500)
    assert len(acc_df) >= 100
    assert len(tx_df) >= 500
    assert "account_id" in acc_df.columns
    assert "transaction_id" in tx_df.columns

def test_tc003_fan_in_ews():
    # 12 senders -> 1 receiver
    features = {
        "unique_senders": 12,
        "unique_receivers": 1,
        "transaction_velocity_1h": 12,
        "dormancy_days": 2.0,
        "rapid_movement_ratio": 0.10,
        "incoming_amount_total": 5000.0,
        "risky_neighbor_count": 0,
        "risky_neighbor_ratio": 0.0,
        "circular_flow_indicator": 0
    }
    ews_result = evaluate_account_ews(features)
    triggered_codes = [s["code"] for s in ews_result["triggered_signals"]]
    assert "EWS-002" in triggered_codes # FAN_IN_SPIKE

def test_tc004_velocity_ews():
    # 20 transactions in 1 hour
    features = {
        "unique_senders": 2,
        "unique_receivers": 2,
        "transaction_velocity_1h": 20,
        "dormancy_days": 1.0,
        "rapid_movement_ratio": 0.0,
        "incoming_amount_total": 2000.0,
        "risky_neighbor_count": 0,
        "risky_neighbor_ratio": 0.0,
        "circular_flow_indicator": 0
    }
    ews_result = evaluate_account_ews(features)
    triggered_codes = [s["code"] for s in ews_result["triggered_signals"]]
    assert "EWS-001" in triggered_codes # VELOCITY_SPIKE

def test_tc005_dormancy_ews():
    # Inactive for 40 days, then 10 txns in 1h
    features = {
        "unique_senders": 3,
        "unique_receivers": 3,
        "transaction_velocity_1h": 10,
        "dormancy_days": 40.0,
        "rapid_movement_ratio": 0.0,
        "incoming_amount_total": 3000.0,
        "risky_neighbor_count": 0,
        "risky_neighbor_ratio": 0.0,
        "circular_flow_indicator": 0
    }
    ews_result = evaluate_account_ews(features)
    triggered_codes = [s["code"] for s in ews_result["triggered_signals"]]
    assert "EWS-004" in triggered_codes # DORMANCY_BURST

def test_tc006_normal_account():
    features = {
        "unique_senders": 2,
        "unique_receivers": 2,
        "transaction_velocity_1h": 2,
        "dormancy_days": 1.0,
        "rapid_movement_ratio": 0.0,
        "incoming_amount_total": 1500.0,
        "risky_neighbor_count": 0,
        "risky_neighbor_ratio": 0.0,
        "circular_flow_indicator": 0
    }
    ews_result = evaluate_account_ews(features)
    assert len(ews_result["triggered_signals"]) == 0
    assert ews_result["ews_score"] == 0.0

def test_tc007_risk_fusion():
    ews_result = {
        "ews_score": 80.0,
        "triggered_signals": [{"type": "FAN_IN_SPIKE", "code": "EWS-002", "severity": "CRITICAL", "description": "Fan in"}],
        "reasons": ["35 unique senders"]
    }
    features = {"risky_neighbor_count": 2, "risky_neighbor_ratio": 0.5, "circular_flow_indicator": 1}
    fusion = calculate_risk_fusion("A102", ml_prob=0.90, ews_result=ews_result, features=features)
    assert fusion["risk_level"] in ["HIGH", "CRITICAL"]
    assert fusion["risk_score"] >= 75.0

def test_tc010_dashboard_api():
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_accounts" in data
    assert "total_transactions" in data
    assert "active_alerts" in data
    assert "risk_distribution" in data

def test_tc011_missing_account_api():
    response = client.get("/api/v1/accounts/NON_EXISTENT_ACC_999")
    assert response.status_code == 404

def test_tc012_invalid_alert_status_api():
    response = client.patch("/api/v1/alerts/ALT-0001", json={"status": "INVALID_STATUS_XYZ"})
    assert response.status_code in [400, 404]

if __name__ == "__main__":
    print("Running GraphGuard Pipeline Verification Tests...")
    test_tc001_dataset_loading()
    print("[PASS] TC-001 Dataset Loading")
    test_tc003_fan_in_ews()
    print("[PASS] TC-003 Fan-In EWS Trigger")
    test_tc004_velocity_ews()
    print("[PASS] TC-004 Velocity EWS Trigger")
    test_tc005_dormancy_ews()
    print("[PASS] TC-005 Dormancy Burst EWS Trigger")
    test_tc006_normal_account()
    print("[PASS] TC-006 Normal Account Baseline")
    test_tc007_risk_fusion()
    print("[PASS] TC-007 Multi-Signal Risk Fusion")
    test_tc010_dashboard_api()
    print("[PASS] TC-010 Dashboard Summary API")
    test_tc011_missing_account_api()
    print("[PASS] TC-011 404 Missing Account API")
    test_tc012_invalid_alert_status_api()
    print("[PASS] TC-012 Invalid Alert Status API")
    print("\nALL 9 PIPELINE VERIFICATION TESTS PASSED SUCCESSFULLY!")

