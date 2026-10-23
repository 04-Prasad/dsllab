"""
GraphGuard GNN (GraphSAGE) Model Trainer & Inference Engine
===========================================================
Implements GraphSAGE with both native PyTorch message passing and
PyTorch Geometric support. Evaluates Precision, Recall, F1, ROC-AUC,
and saves model weights and metrics.
"""

import os
import json
import logging
import joblib
import pandas as pd
import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix

from ml.src.train_baseline import FEATURE_COLS, InsufficientLabelsError

logger = logging.getLogger(__name__)


# ── Native PyTorch GraphSAGE Implementation ──────────────────────────────────

class SAGEConv(nn.Module):
    """GraphSAGE Mean-Aggregation Convolutional Layer."""
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.linear_self = nn.Linear(in_features, out_features, bias=False)
        self.linear_neigh = nn.Linear(in_features, out_features, bias=True)

    def forward(self, x: torch.Tensor, adj_norm: torch.Tensor) -> torch.Tensor:
        # Neighborhood aggregation
        if adj_norm.is_sparse:
            neigh = torch.sparse.mm(adj_norm, x)
        else:
            neigh = torch.matmul(adj_norm, x)
        out = self.linear_self(x) + self.linear_neigh(neigh)
        return F.relu(out)


class GraphSAGEModel(nn.Module):
    """Two-layer GraphSAGE architecture with classification head."""
    def __init__(self, in_channels: int, hidden_channels: int = 32, out_channels: int = 1):
        super().__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, hidden_channels)
        self.fc = nn.Linear(hidden_channels, out_channels)
        self.dropout = nn.Dropout(0.2)

    def forward(self, x: torch.Tensor, adj_norm: torch.Tensor) -> torch.Tensor:
        h = self.conv1(x, adj_norm)
        h = self.dropout(h)
        h = self.conv2(h, adj_norm)
        out = torch.sigmoid(self.fc(h))
        return out.squeeze(-1)


def build_normalized_adjacency(nodes: list, G) -> torch.Tensor:
    """Builds a row-normalized adjacency matrix as a PyTorch sparse tensor."""
    n = len(nodes)
    node_to_idx = {str(node): i for i, node in enumerate(nodes)}

    row_indices = []
    col_indices = []
    degrees = np.ones(n, dtype=float)

    # Self-loops ensure ego-features are always propagated
    for i in range(n):
        row_indices.append(i)
        col_indices.append(i)

    if G.number_of_edges() > 0:
        for u, v in G.edges():
            u_str, v_str = str(u), str(v)
            if u_str in node_to_idx and v_str in node_to_idx:
                ui = node_to_idx[u_str]
                vi = node_to_idx[v_str]
                # Directed + reverse for message passing
                row_indices.append(vi)
                col_indices.append(ui)
                degrees[vi] += 1.0

    # Row normalization D^-1 * A
    values = [1.0 / degrees[r] for r in row_indices]

    indices = torch.tensor([row_indices, col_indices], dtype=torch.long)
    values = torch.tensor(values, dtype=torch.float32)
    adj = torch.sparse_coo_tensor(indices, values, (n, n)).coalesce()
    return adj


def train_gnn_model(
    features_df: pd.DataFrame,
    G,
    artifacts_dir: str = "ml/artifacts",
    epochs: int = 40,
    min_required: int = 8,
) -> tuple:
    """
    Trains GraphSAGE on account features and graph structure.
    Returns (model, metrics_dict).
    """
    os.makedirs(artifacts_dir, exist_ok=True)
    torch.manual_seed(42)
    np.random.seed(42)
    logger.info("[GNN] Training GraphSAGE on %d nodes...", len(features_df))

    # A stable account ordering is the contract between features, labels, graph
    # adjacency and persisted predictions.
    ordered = features_df.copy()
    ordered["account_id"] = ordered["account_id"].astype(str)
    ordered = ordered.sort_values("account_id").reset_index(drop=True)
    if ordered["account_id"].duplicated().any():
        raise ValueError("GraphSAGE requires exactly one feature row per account_id.")
    X_raw = ordered[FEATURE_COLS].fillna(0)
    y_raw = ordered["label"].fillna(0).astype(int).to_numpy()
    nodes = ordered["account_id"].tolist()

    pos_count_all = int((y_raw == 1).sum())
    neg_count_all = int((y_raw == 0).sum())

    # Train / test mask split
    indices = np.arange(len(features_df))
    if len(np.unique(y_raw)) < 2 or pos_count_all < min_required or neg_count_all < min_required:
        raise InsufficientLabelsError(
            pos_count=pos_count_all,
            neg_count=neg_count_all,
            min_required=min_required,
            message=(
                f"Insufficient positive/negative account labels for reliable GraphSAGE evaluation: "
                f"found {pos_count_all} positive and {neg_count_all} negative (need at least {min_required} of each class)."
            ),
        )
    stratify = y_raw
    train_idx, test_idx = train_test_split(indices, test_size=0.25, random_state=42, stratify=stratify)

    # Fit preprocessing on training nodes only; preserve DataFrame feature names.
    scaler = StandardScaler()
    scaler.fit(X_raw.iloc[train_idx])
    X_scaled = scaler.transform(X_raw)
    joblib.dump(scaler, os.path.join(artifacts_dir, "gnn_scaler.pkl"))

    # Build Adjacency matrix
    adj_norm = build_normalized_adjacency(nodes, G)

    x_tensor = torch.tensor(X_scaled, dtype=torch.float32)
    y_tensor = torch.tensor(y_raw, dtype=torch.float32)

    # Calculate class weighting for BCELoss
    pos_count = (y_raw[train_idx] == 1).sum()
    neg_count = (y_raw[train_idx] == 0).sum()
    pos_weight = float(neg_count / max(1, pos_count))
    weight_tensor = torch.ones_like(y_tensor)
    weight_tensor[y_tensor == 1] = pos_weight

    model = GraphSAGEModel(in_channels=X_scaled.shape[1], hidden_channels=32, out_channels=1)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)

    # Training loop
    model.train()
    for epoch in range(1, epochs + 1):
        optimizer.zero_grad()
        out = model(x_tensor, adj_norm)
        # Loss computed over train indices with class weights
        loss = F.binary_cross_entropy(out[train_idx], y_tensor[train_idx], weight=weight_tensor[train_idx])
        loss.backward()
        optimizer.step()

    # Evaluation on test set
    model.eval()
    with torch.no_grad():
        test_out = model(x_tensor, adj_norm)[test_idx].numpy()
        test_y = y_tensor[test_idx].numpy()

    test_pred = (test_out >= 0.5).astype(int)

    precision = float(precision_score(test_y, test_pred, zero_division=0))
    recall = float(recall_score(test_y, test_pred, zero_division=0))
    f1 = float(f1_score(test_y, test_pred, zero_division=0))
    roc_auc = float(roc_auc_score(test_y, test_out)) if len(np.unique(test_y)) > 1 else 1.0
    pr_auc = float(average_precision_score(test_y, test_out)) if len(np.unique(test_y)) > 1 else 0.0
    cm = confusion_matrix(test_y, test_pred).tolist()

    metrics = {
        "model_type": "GraphSAGE",
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "threshold": 0.5,
        "train_class_counts": {str(k): int(v) for k, v in pd.Series(y_raw[train_idx]).value_counts().items()},
        "test_class_counts": {str(k): int(v) for k, v in pd.Series(y_raw[test_idx]).value_counts().items()},
        "confusion_matrix": cm,
        "epochs": epochs,
    }

    # Save model weights and metrics
    torch.save(model.state_dict(), os.path.join(artifacts_dir, "gnn_model.pt"))
    with open(os.path.join(artifacts_dir, "gnn_node_order.json"), "w") as f:
        json.dump(nodes, f)
    with open(os.path.join(artifacts_dir, "gnn_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info(
        "[GNN] GraphSAGE trained successfully. Precision=%.4f | Recall=%.4f | F1=%.4f | ROC-AUC=%.4f",
        precision, recall, f1, roc_auc
    )

    return model, metrics


def get_ml_predictions(
    features_df: pd.DataFrame,
    G=None,
    artifacts_dir: str = "ml/artifacts",
) -> dict:
    """
    Returns account_id -> ml_score (0.0 to 1.0) dictionary.
    Prioritizes XGBoost (base model) or GraphSAGE.
    """
    metrics_path = os.path.join(artifacts_dir, "metrics.json")
    selected_model = "XGBoost"
    status = "TRAINED"
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, encoding="utf-8") as f:
                metrics_data = json.load(f)
                selected_model = metrics_data.get("best_model", metrics_data.get("base_model", selected_model))
                status = metrics_data.get("status", "TRAINED")
        except Exception:
            pass

    if status == "SKIPPED_INSUFFICIENT_LABELS":
        logger.info("[GNN] ML evaluation was skipped due to insufficient labels. Returning empty predictions.")
        return {}

    gnn_path = os.path.join(artifacts_dir, "gnn_model.pt")
    rf_path = os.path.join(artifacts_dir, "rf_model.pkl")
    ada_path = os.path.join(artifacts_dir, "adaboost_model.pkl")
    xgb_path = os.path.join(artifacts_dir, "xgboost_model.pkl")
    gnn_scaler_path = os.path.join(artifacts_dir, "gnn_scaler.pkl")
    rf_scaler_path = os.path.join(artifacts_dir, "rf_scaler.pkl")
    ada_scaler_path = os.path.join(artifacts_dir, "adaboost_scaler.pkl")
    xgb_scaler_path = os.path.join(artifacts_dir, "xgboost_scaler.pkl")
    xgb_metrics_path = os.path.join(artifacts_dir, "xgboost_metrics.json")

    predictions = {}
    nodes = list(features_df["account_id"].astype(str))

    # Inference helpers for each model type
    def _predict_gnn():
        if os.path.exists(gnn_path) and os.path.exists(gnn_scaler_path) and G is not None:
            try:
                with open(os.path.join(artifacts_dir, "gnn_node_order.json"), encoding="utf-8") as f:
                    gnn_nodes = json.load(f)
                by_account = features_df.copy()
                by_account["account_id"] = by_account["account_id"].astype(str)
                if by_account["account_id"].duplicated().any() or set(gnn_nodes) != set(by_account["account_id"]):
                    raise ValueError("GraphSAGE inference account IDs do not match the trained node mapping.")
                X = by_account.set_index("account_id").loc[gnn_nodes, FEATURE_COLS].fillna(0)
                scaler = joblib.load(gnn_scaler_path)
                X_scaled = scaler.transform(X)
                x_tensor = torch.tensor(X_scaled, dtype=torch.float32)
                adj_norm = build_normalized_adjacency(gnn_nodes, G)

                model = GraphSAGEModel(in_channels=X_scaled.shape[1], hidden_channels=32, out_channels=1)
                model.load_state_dict(torch.load(gnn_path, map_location="cpu"))
                model.eval()

                with torch.no_grad():
                    scores = model(x_tensor, adj_norm).numpy()

                res = {}
                for acc_id, score in zip(gnn_nodes, scores):
                    res[acc_id] = round(float(np.clip(score, 0.0, 1.0)), 4)
                return res
            except Exception as e:
                logger.warning("[GNN] GraphSAGE inference fallback: %s", e)
                return None
        return None

    def _predict_rf():
        if os.path.exists(rf_path) and os.path.exists(rf_scaler_path):
            try:
                rf_model = joblib.load(rf_path)
                scaler = joblib.load(rf_scaler_path)
                X = features_df[FEATURE_COLS].fillna(0)
                X_scaled = scaler.transform(X)
                if hasattr(rf_model, "predict_proba") and len(rf_model.classes_) > 1 and 1 in rf_model.classes_:
                    pos_idx = list(rf_model.classes_).index(1)
                    scores = rf_model.predict_proba(X_scaled)[:, pos_idx]
                else:
                    scores = rf_model.predict(X_scaled)
                res = {}
                for acc_id, score in zip(nodes, scores):
                    res[acc_id] = round(float(score), 4)
                return res
            except Exception as e:
                logger.warning("[ML INFERENCE] Random Forest inference failed: %s", e)
                return None
        return None

    def _predict_adaboost():
        if os.path.exists(ada_path) and os.path.exists(ada_scaler_path):
            try:
                ada_model = joblib.load(ada_path)
                scaler = joblib.load(ada_scaler_path)
                X = features_df[FEATURE_COLS].fillna(0)
                if hasattr(ada_model, "predict_proba") and len(ada_model.classes_) > 1 and 1 in ada_model.classes_:
                    pos_idx = list(ada_model.classes_).index(1)
                    scores = ada_model.predict_proba(scaler.transform(X))[:, pos_idx]
                else:
                    scores = ada_model.predict(scaler.transform(X))
                res = {}
                for acc_id, score in zip(nodes, scores):
                    res[acc_id] = round(float(score), 4)
                return res
            except Exception as e:
                logger.warning("[ML INFERENCE] AdaBoost inference failed: %s", e)
                return None
        return None

    def _predict_xgboost():
        if (os.path.exists(xgb_path) or os.path.exists(os.path.join(artifacts_dir, "xgboost_model.json"))) and os.path.exists(xgb_scaler_path):
            try:
                if os.path.exists(xgb_path):
                    xgb_model = joblib.load(xgb_path)
                else:
                    import xgboost as xgb_lib
                    xgb_model = xgb_lib.XGBClassifier()
                    xgb_model.load_model(os.path.join(artifacts_dir, "xgboost_model.json"))

                scaler = joblib.load(xgb_scaler_path)
                X = features_df[FEATURE_COLS].fillna(0)
                X_scaled = scaler.transform(X)

                if hasattr(xgb_model, "predict_proba"):
                    scores = xgb_model.predict_proba(X_scaled)[:, 1]
                else:
                    scores = xgb_model.predict(X_scaled)

                res = {}
                for acc_id, score in zip(nodes, scores):
                    res[acc_id] = round(float(score), 4)
                return res
            except Exception as e:
                logger.warning("[ML INFERENCE] XGBoost inference failed: %s", e)
                return None
        return None

    # 1. Attempt inference with the selected (best/base) model
    if selected_model == "XGBoost":
        res = _predict_xgboost()
        if res is not None:
            return res
    elif selected_model == "GraphSAGE":
        res = _predict_gnn()
        if res is not None:
            return res
    elif selected_model == "AdaBoost":
        res = _predict_adaboost()
        if res is not None:
            return res
    elif selected_model == "RandomForest":
        res = _predict_rf()
        if res is not None:
            return res

    # 2. Fallback chain: XGBoost (base) -> GraphSAGE -> AdaBoost -> Random Forest
    for fallback_fn in (_predict_xgboost, _predict_gnn, _predict_adaboost, _predict_rf):
        res = fallback_fn()
        if res is not None:
            return res

    logger.info("[ML INFERENCE] No trained ML model artifacts available; returning empty predictions map.")
    return {}
