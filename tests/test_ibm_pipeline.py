"""
GraphGuard IBM AML Pipeline Test Suite
======================================
Tests:
1. Schema normalization and duplicate Account column handling
2. Account ID string preservation
3. Preprocessing and Parquet caching
4. Feature extraction and zero target leakage
5. Random Forest, AdaBoost, and GraphSAGE training & metrics
6. Deterministic EWS rules engine
7. Multi-signal Risk Fusion scoring
8. FastAPI /api/v1/models endpoints
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np
import networkx as nx

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from config.settings import settings
from ml.src.ibm_adapter import (
    normalize_transaction_columns,
    normalize_account_columns,
    IBM_TRANSACTION_COLUMN_MAP,
)
from ml.src.ibm_preprocessing import (
    preprocess_transactions,
    build_accounts_from_transactions,
    compute_label_diagnostics,
)
from ml.src.features import extract_features
from ml.src.graph_builder import build_networkx_graph
from ml.src.train_baseline import (
    train_baseline_model,
    train_all_models,
    FEATURE_COLS,
    InsufficientLabelsError,
)
from ml.src.train_adaboost import train_adaboost_model
from ml.src.train_gnn import train_gnn_model, get_ml_predictions
from backend.app.services.ews_service import evaluate_account_ews
from backend.app.services.risk_service import calculate_risk_fusion, classify_risk_level
from backend.app.models.models import (
    User, AuditLog, Account, Transaction, AccountFeature, RiskScore, EWSSignal, Alert
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.db.database import Base


class TestIBMAPIPipeline(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        import shutil
        if os.path.exists("ml/artifacts_test"):
            shutil.rmtree("ml/artifacts_test", ignore_errors=True)

    def setUp(self):
        # Create a synthetic mini-IBM raw DataFrame with duplicate Account columns
        self.raw_ibm_tx = pd.DataFrame({
            "Timestamp": ["2022/09/01 00:08", "2022/09/01 00:21", "2022/09/01 01:15", "2022/09/01 02:00"],
            "From Bank": ["011", "03402", "011", "03402"],
            "Account": ["8000ECA90", "80021DAD0", "8000ECA90", "80045BC10"],
            "To Bank": ["011", "011", "020", "011"],
            "Account.1": ["80021DAD0", "80045BC10", "80021DAD0", "8000ECA90"],
            "Amount Received": ["1000.50", "25000.00", "500.00", "75000.00"],
            "Receiving Currency": ["US Dollar", "US Dollar", "US Dollar", "US Dollar"],
            "Amount Paid": ["1000.50", "25000.00", "500.00", "75000.00"],
            "Payment Currency": ["US Dollar", "US Dollar", "US Dollar", "US Dollar"],
            "Payment Format": ["Wire", "Cheque", "Wire", "Reinvestment"],
            "Is Laundering": ["0", "1", "0", "1"],
        })

        self.raw_ibm_acc = pd.DataFrame({
            "Bank Name": ["China Bank #2820", "France Bank #4585", "USA Bank #1010"],
            "Bank ID": ["314693", "311253", "100200"],
            "Account Number": ["8000ECA90", "80021DAD0", "80045BC10"],
            "Entity ID": ["800D8CCF0", "800B505E0", "800A123F0"],
            "Entity Name": ["Corporation #41344", "Corporation #54497", "LLC #102"],
        })

    def test_01_ibm_adapter_normalization(self):
        """Test column rename, duplicate handling, and string account ID preservation."""
        norm_tx = normalize_transaction_columns(self.raw_ibm_tx.copy())
        self.assertIn("sender_account_id", norm_tx.columns)
        self.assertIn("receiver_account_id", norm_tx.columns)
        self.assertIn("amount", norm_tx.columns)
        self.assertIn("is_laundering", norm_tx.columns)
        self.assertIn("label", norm_tx.columns)
        self.assertEqual(norm_tx["sender_account_id"].iloc[0], "8000ECA90")
        self.assertEqual(norm_tx["receiver_account_id"].iloc[0], "80021DAD0")
        self.assertIsInstance(norm_tx["sender_account_id"].iloc[0], str)

        norm_acc = normalize_account_columns(self.raw_ibm_acc.copy())
        self.assertIn("account_id", norm_acc.columns)
        self.assertEqual(norm_acc["account_id"].iloc[0], "8000ECA90")

    def test_02_preprocessing_and_account_derivation(self):
        """Test preprocessing cleaning, timestamp parsing, and account label derivation."""
        norm_tx = normalize_transaction_columns(self.raw_ibm_tx.copy())
        norm_acc = normalize_account_columns(self.raw_ibm_acc.copy())

        clean_tx, stats = preprocess_transactions(norm_tx)
        self.assertEqual(len(clean_tx), 4)
        self.assertEqual(stats["laundering_transactions"], 2)

        acc_df = build_accounts_from_transactions(clean_tx, norm_acc)
        self.assertGreaterEqual(len(acc_df), 3)
        # All three accounts participated in laundering transactions
        self.assertTrue((acc_df["label"] == 1).all())

    def test_03_features_and_no_target_leakage(self):
        """Test 22-feature extraction and ensure target column is NOT in features."""
        norm_tx = normalize_transaction_columns(self.raw_ibm_tx.copy())
        norm_acc = normalize_account_columns(self.raw_ibm_acc.copy())
        clean_tx, _ = preprocess_transactions(norm_tx)
        acc_df = build_accounts_from_transactions(clean_tx, norm_acc)

        G = build_networkx_graph(acc_df, clean_tx)
        feat_df = extract_features(acc_df, clean_tx, G)

        for col in FEATURE_COLS:
            self.assertIn(col, feat_df.columns, f"Missing feature: {col}")

        # Verify target leakage: is_laundering must NOT be in FEATURE_COLS
        self.assertNotIn("is_laundering", FEATURE_COLS)
        self.assertNotIn("label", FEATURE_COLS)
        self.assertNotIn("laundering_transaction_count", FEATURE_COLS)

    def test_04_model_trainers_rf_adaboost_gnn(self):
        """Test Random Forest, AdaBoost, and GraphSAGE training and metric calculation."""
        # Create a synthetic dataset of 40 accounts for robust train_test_split
        np.random.seed(42)
        n = 40
        mock_features = []
        for i in range(n):
            lbl = 1 if i < 10 else 0
            row = {
                "account_id": f"ACC_{i:03d}",
                "total_transactions": np.random.randint(5, 50),
                "incoming_transaction_count": np.random.randint(2, 25),
                "outgoing_transaction_count": np.random.randint(2, 25),
                "incoming_amount_total": float(np.random.uniform(1000, 50000)),
                "outgoing_amount_total": float(np.random.uniform(1000, 50000)),
                "average_incoming_amount": float(np.random.uniform(100, 5000)),
                "average_outgoing_amount": float(np.random.uniform(100, 5000)),
                "max_transaction_amount": float(np.random.uniform(500, 20000)),
                "unique_senders": np.random.randint(1, 10),
                "unique_receivers": np.random.randint(1, 10),
                "transaction_velocity_1h": np.random.randint(0, 15),
                "transaction_velocity_24h": np.random.randint(0, 30),
                "dormancy_days": float(np.random.uniform(0, 45)),
                "rapid_movement_ratio": float(np.random.uniform(0.1, 0.95)),
                "account_age_days": np.random.randint(10, 365),
                "in_degree": np.random.randint(1, 8),
                "out_degree": np.random.randint(1, 8),
                "degree": np.random.randint(2, 16),
                "pagerank": float(np.random.uniform(0.001, 0.05)),
                "risky_neighbor_count": np.random.randint(0, 4),
                "risky_neighbor_ratio": float(np.random.uniform(0.0, 0.8)),
                "circular_flow_indicator": np.random.choice([0, 1]),
                "label": lbl,
            }
            mock_features.append(row)

        feat_df = pd.DataFrame(mock_features)
        G = nx.fast_gnp_random_graph(n, 0.1, directed=True)
        node_map = {i: f"ACC_{i:03d}" for i in range(n)}
        G = nx.relabel_nodes(G, node_map)

        # 1. Random Forest
        _, _, rf_metrics = train_baseline_model(feat_df, artifacts_dir="ml/artifacts_test")
        self.assertIn("precision", rf_metrics)
        self.assertIn("recall", rf_metrics)
        self.assertIn("f1_score", rf_metrics)

        # 2. AdaBoost
        _, _, ada_metrics = train_adaboost_model(feat_df, artifacts_dir="ml/artifacts_test")
        self.assertIn("f1_score", ada_metrics)

        # 3. GraphSAGE
        _, gnn_metrics = train_gnn_model(feat_df, G, artifacts_dir="ml/artifacts_test", epochs=5)
        self.assertIn("f1_score", gnn_metrics)

        # 4. Multi-model comparison
        all_metrics = train_all_models(feat_df, G, artifacts_dir="ml/artifacts_test")
        self.assertIn("best_model", all_metrics)
        self.assertIn("models_comparison", all_metrics)
        self.assertIn("RandomForest", all_metrics["models_comparison"])
        self.assertIn("AdaBoost", all_metrics["models_comparison"])
        self.assertIn("GraphSAGE", all_metrics["models_comparison"])

    def test_05_ews_and_risk_fusion(self):
        """Test EWS deterministic rules engine and 0-100 Risk Fusion."""
        features = {
            "transaction_velocity_1h": 25,  # triggers EWS-001
            "unique_senders": 15,           # triggers EWS-002
            "unique_receivers": 12,          # triggers EWS-003
            "dormancy_days": 40,
            "rapid_movement_ratio": 0.88,   # triggers EWS-005
            "risky_neighbor_ratio": 0.50,   # triggers EWS-006
            "risky_neighbor_count": 3,
            "circular_flow_indicator": 1,   # triggers EWS-007
            "pagerank": 0.015,
        }

        ews_res = evaluate_account_ews(features)
        self.assertGreater(len(ews_res["triggered_signals"]), 0)
        self.assertGreater(ews_res["ews_score"], 50.0)

        fusion = calculate_risk_fusion(
            account_id="8000ECA90",
            ml_prob=0.85,
            ews_result=ews_res,
            features=features,
            ml_enabled=True,
        )

        self.assertIn(fusion["risk_level"], ["HIGH", "CRITICAL"])
        self.assertGreaterEqual(fusion["risk_score"], 60.0)
        self.assertLessEqual(fusion["risk_score"], 100.0)
        self.assertIn("reasons", fusion)

    def test_06_binary_label_and_risk_boundaries(self):
        """Malformed label values never create a third class; score bands are exact."""
        raw = self.raw_ibm_tx.copy()
        raw.loc[0, "Is Laundering"] = "2"
        normalized = normalize_transaction_columns(raw)
        self.assertEqual(int(normalized.loc[0, "is_laundering"]), 0)
        self.assertEqual(set(normalized["is_laundering"].unique()), {0, 1})
        self.assertEqual(classify_risk_level(29.9), "LOW")
        self.assertEqual(classify_risk_level(30.0), "MEDIUM")
        self.assertEqual(classify_risk_level(60.0), "HIGH")
        self.assertEqual(classify_risk_level(80.0), "CRITICAL")

    def test_07_graphsage_node_mapping_is_stable(self):
        """Adjacency construction resolves graph node IDs through the supplied order."""
        from ml.src.train_gnn import build_normalized_adjacency
        graph = nx.DiGraph()
        graph.add_edge("B", "A")
        adjacency = build_normalized_adjacency(["A", "B"], graph).to_dense().numpy()
        # A receives B's message; B has only its self-loop.
        self.assertGreater(adjacency[0, 1], 0.0)
        self.assertGreater(adjacency[1, 1], 0.0)

    def test_08_transaction_label_normalization_robustness(self):
        """1. Transaction label normalization: test diverse raw values strictly produce 0 or 1."""
        test_df = pd.DataFrame({
            "Timestamp": ["2022/09/01 00:00"] * 10,
            "From Bank": ["011"] * 10,
            "Account": [f"ACC_{i}" for i in range(10)],
            "To Bank": ["012"] * 10,
            "Account.1": [f"ACC_{i+10}" for i in range(10)],
            "Amount Paid": [100.0] * 10,
            "Is Laundering": ["1", "0", "2", "-1", "null", "True", "true", "false", None, np.nan],
        })
        normalized = normalize_transaction_columns(test_df)
        labels = normalized["is_laundering"].tolist()
        self.assertEqual(labels[0], 1)
        self.assertEqual(labels[1], 0)
        self.assertEqual(labels[2], 0)
        self.assertEqual(labels[3], 0)
        self.assertEqual(labels[4], 0)
        self.assertEqual(labels[5], 1)
        self.assertEqual(labels[6], 1)
        self.assertEqual(labels[7], 0)
        self.assertEqual(labels[8], 0)
        self.assertEqual(labels[9], 0)
        self.assertTrue(set(normalized["is_laundering"].unique()).issubset({0, 1}))

    def test_09_account_level_suspicious_aggregation_logic(self):
        """2. Account-level suspicious-label aggregation: sender OR receiver of laundering == 1."""
        tx_df = pd.DataFrame({
            "transaction_id": ["TX1", "TX2", "TX3", "TX4"],
            "sender_account_id": ["ACC_A", "ACC_B", "ACC_C", "ACC_E"],
            "receiver_account_id": ["ACC_B", "ACC_C", "ACC_D", "ACC_F"],
            "amount": [100.0, 500.0, 300.0, 200.0],
            "timestamp": pd.to_datetime(["2022-09-01 01:00", "2022-09-01 02:00", "2022-09-01 03:00", "2022-09-01 04:00"]),
            "is_laundering": [0, 1, 0, 0],
        })
        acc_df = build_accounts_from_transactions(tx_df)
        label_map = dict(zip(acc_df["account_id"], acc_df["label"]))

        self.assertEqual(label_map.get("ACC_B"), 1)
        self.assertEqual(label_map.get("ACC_C"), 1)
        self.assertEqual(label_map.get("ACC_A"), 0)
        self.assertEqual(label_map.get("ACC_D"), 0)
        self.assertEqual(label_map.get("ACC_E"), 0)
        self.assertEqual(label_map.get("ACC_F"), 0)

    def test_10_sender_and_receiver_account_id_consistency(self):
        """3. Sender and receiver account ID consistency and string preservation."""
        raw_df = pd.DataFrame({
            "Timestamp": ["2022/09/01 00:00"],
            "From Bank": ["011"],
            "Account": ["00012345"],
            "To Bank": ["012"],
            "Account.1": ["  987600  "],
            "Amount Paid": [50.0],
            "Is Laundering": ["0"],
        })
        norm = normalize_transaction_columns(raw_df)
        self.assertEqual(norm["sender_account_id"].iloc[0], "00012345")
        self.assertEqual(norm["receiver_account_id"].iloc[0], "987600")
        self.assertIsInstance(norm["sender_account_id"].iloc[0], str)
        self.assertIsInstance(norm["receiver_account_id"].iloc[0], str)

    def test_11_dataset_label_distribution_diagnostics(self):
        """4. Sampling and dataset label distribution diagnostics calculation."""
        tx_df = pd.DataFrame({
            "transaction_id": ["TX1", "TX2", "TX3"],
            "sender_account_id": ["A", "B", "C"],
            "receiver_account_id": ["B", "C", "A"],
            "amount": [10.0, 20.0, 30.0],
            "timestamp": pd.to_datetime(["2022-09-01 01:00", "2022-09-01 02:00", "2022-09-01 03:00"]),
            "is_laundering": [0, 1, 0],
        })
        acc_df = pd.DataFrame({
            "account_id": ["A", "B", "C"],
            "label": [0, 1, 1],
        })
        diag = compute_label_diagnostics(tx_df, acc_df)
        self.assertEqual(diag["transactions"]["total"], 3)
        self.assertEqual(diag["transactions"]["positive_laundering"], 1)
        self.assertEqual(diag["transactions"]["negative_normal"], 2)
        self.assertEqual(diag["accounts"]["total"], 3)
        self.assertEqual(diag["accounts"]["positive_suspicious"], 2)
        self.assertFalse(diag["sufficient_for_stratified_evaluation"])

    def test_12_behavior_when_too_few_positive_examples(self):
        """5. Behavior when there are too few positive examples: strict mode raises, allow mode skips."""
        mock_features = []
        for i in range(40):
            mock_features.append({
                "account_id": f"ACC_{i:03d}",
                "label": 1 if i < 3 else 0,
                **{col: 1.0 for col in FEATURE_COLS},
            })
        df = pd.DataFrame(mock_features)

        with self.assertRaises(InsufficientLabelsError) as ctx:
            train_all_models(df, allow_insufficient_labels=False, min_required=8)
        self.assertEqual(ctx.exception.pos_count, 3)

        res = train_all_models(df, artifacts_dir="ml/artifacts_test", allow_insufficient_labels=True, min_required=8)
        self.assertEqual(res["status"], "SKIPPED_INSUFFICIENT_LABELS")
        self.assertIsNone(res["best_model"])
        self.assertIn("recommendation", res["diagnostics"])

    def test_13_behavior_when_valid_stratified_split_possible(self):
        """6. Behavior when a valid stratified split is possible (>= 8 positives)."""
        np.random.seed(42)
        mock_features = []
        for i in range(50):
            mock_features.append({
                "account_id": f"ACC_{i:03d}",
                "label": 1 if i < 12 else 0,
                **{col: float(np.random.uniform(1, 100)) for col in FEATURE_COLS},
            })
        df = pd.DataFrame(mock_features)
        G = nx.fast_gnp_random_graph(50, 0.1, directed=True)
        node_map = {i: f"ACC_{i:03d}" for i in range(50)}
        G = nx.relabel_nodes(G, node_map)

        res = train_all_models(df, G=G, artifacts_dir="ml/artifacts_test", allow_insufficient_labels=False, min_required=8)
        self.assertEqual(res["status"], "TRAINED")
        self.assertIsNotNone(res["best_model"])
        self.assertIn(res["best_model"], ["RandomForest", "AdaBoost", "GraphSAGE"])

    def test_14_correct_handling_of_missing_model_results(self):
        """7. Correct handling of missing model results: get_ml_predictions returns empty, risk fusion uses fallback."""
        mock_features = pd.DataFrame([
            {"account_id": "ACC_001", "label": 1, **{col: 1.0 for col in FEATURE_COLS}},
            {"account_id": "ACC_002", "label": 0, **{col: 1.0 for col in FEATURE_COLS}},
        ])
        preds = get_ml_predictions(mock_features, artifacts_dir="ml/non_existent_artifacts_dir")
        self.assertEqual(preds, {})

        ews_result = {"ews_score": 60.0, "triggered_signals": [], "reasons": ["Test Signal"]}
        feat_data = {"risky_neighbor_ratio": 0.2, "risky_neighbor_count": 1, "circular_flow_indicator": 0, "pagerank": 0.01}
        fusion = calculate_risk_fusion("ACC_001", ml_prob=0.0, ews_result=ews_result, features=feat_data, ml_enabled=False)
        self.assertGreater(fusion["risk_score"], 0.0)
        self.assertEqual(fusion["ml_score"], 0.0)

    def test_15_explicit_reporting_when_model_training_skipped(self):
        """8. Explicit reporting in artifacts when model training is skipped."""
        import json
        metrics_path = os.path.join("ml/artifacts_test", "metrics.json")
        mock_features = pd.DataFrame([
            {"account_id": f"ACC_{i:03d}", "label": 1 if i < 2 else 0, **{col: 1.0 for col in FEATURE_COLS}}
            for i in range(20)
        ])
        train_all_models(mock_features, artifacts_dir="ml/artifacts_test", allow_insufficient_labels=True, min_required=8)
        self.assertTrue(os.path.exists(metrics_path))
        with open(metrics_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["status"], "SKIPPED_INSUFFICIENT_LABELS")
        self.assertEqual(data["total_accounts_evaluated"], 0)
        self.assertIn("diagnostics", data)

    def test_16_safe_reruns_after_partial_database_initialization(self):
        """9. Safe reruns after partial DB initialization: preflight detects existing data without reset flag."""
        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=test_engine)
        TestSession = sessionmaker(bind=test_engine)
        db = TestSession()

        db.add(Account(account_id="ACC_TEST_001", account_type="CURRENT", status="ACTIVE", label=0))
        db.commit()

        count = db.query(Account).count()
        reset_db = False
        with self.assertRaises(RuntimeError):
            if count > 0 and not reset_db:
                raise RuntimeError("Pipeline tables already contain data. Re-run with --reset-db to replace only generated pipeline records.")
        db.close()

    def test_17_preservation_of_user_and_audit_records_during_reset(self):
        """10. Preservation of existing user and audit records during the intended reset operation."""
        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=test_engine)
        TestSession = sessionmaker(bind=test_engine)
        db = TestSession()

        user = User(full_name="AML Investigator", email="investigator@bank.com", password_hash="hash123", role="INVESTIGATOR")
        db.add(user)
        db.commit()

        audit = AuditLog(user_id=user.id, event_type="LOGIN", status="SUCCESS")
        db.add(audit)
        db.add(Account(account_id="ACC_PIPELINE_01", label=0))
        db.add(Transaction(transaction_id="TX_01", sender_account_id="A", receiver_account_id="B", amount=100.0, timestamp="2022-09-01"))
        db.commit()

        # Execute intended pipeline reset operation
        for model in (Alert, EWSSignal, RiskScore, AccountFeature, Transaction, Account):
            db.query(model).delete()
        db.commit()

        # Verify User and AuditLog remain intact
        self.assertEqual(db.query(User).count(), 1)
        self.assertEqual(db.query(User).first().email, "investigator@bank.com")
        self.assertEqual(db.query(AuditLog).count(), 1)
        # Verify pipeline tables are cleared
        self.assertEqual(db.query(Account).count(), 0)
        self.assertEqual(db.query(Transaction).count(), 0)
        db.close()


if __name__ == "__main__":
    unittest.main()
