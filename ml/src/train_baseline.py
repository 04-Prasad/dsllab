"""
GraphGuard Baseline ML Model Trainer
Trains Random Forest classifier on extracted account features.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

FEATURE_COLS = [
    "total_transactions",
    "incoming_transaction_count",
    "outgoing_transaction_count",
    "incoming_amount_total",
    "outgoing_amount_total",
    "average_incoming_amount",
    "average_outgoing_amount",
    "max_transaction_amount",
    "unique_senders",
    "unique_receivers",
    "transaction_velocity_1h",
    "transaction_velocity_24h",
    "dormancy_days",
    "rapid_movement_ratio",
    "account_age_days",
    "in_degree",
    "out_degree",
    "degree",
    "pagerank",
    "risky_neighbor_count",
    "risky_neighbor_ratio",
    "circular_flow_indicator"
]

def train_baseline_model(features_df: pd.DataFrame, artifacts_dir: str = "ml/artifacts"):
    os.makedirs(artifacts_dir, exist_ok=True)

    X = features_df[FEATURE_COLS].fillna(0)
    y = features_df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    clf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced")
    clf.fit(X_train_scaled, y_train)

    y_pred = clf.predict(X_test_scaled)
    y_proba = clf.predict_proba(X_test_scaled)[:, 1] if len(clf.classes_) > 1 else y_pred

    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_proba)) if len(np.unique(y_test)) > 1 else 1.0
    cm = confusion_matrix(y_test, y_pred).tolist()

    metrics = {
        "model_type": "RandomForestClassifier",
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "confusion_matrix": cm,
        "feature_cols": FEATURE_COLS
    }

    joblib.dump(scaler, os.path.join(artifacts_dir, "scaler.pkl"))
    joblib.dump(clf, os.path.join(artifacts_dir, "rf_model.pkl"))

    with open(os.path.join(artifacts_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    with open(os.path.join(artifacts_dir, "feature_schema.json"), "w") as f:
        json.dump(FEATURE_COLS, f, indent=2)

    print(f"[Baseline Model] Trained Random Forest. F1: {f1:.4f}, ROC-AUC: {roc_auc:.4f}")
    return clf, scaler, metrics

if __name__ == "__main__":
    from ml.src.generate_data import generate_dataset
    from ml.src.graph_builder import build_networkx_graph
    from ml.src.features import extract_features

    acc_df, tx_df = generate_dataset()
    G = build_networkx_graph(acc_df, tx_df)
    feat_df = extract_features(acc_df, tx_df, G)
    train_baseline_model(feat_df)
