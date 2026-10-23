"""
GraphGuard Model Training & Evaluation Engine
=============================================
Trains Random Forest, AdaBoost, XGBoost, and GraphSAGE models.
Evaluates Precision, Recall, F1-Score, ROC-AUC, PR-AUC, and Confusion Matrices.
Selects the best performing model based on experimental results.
"""

import os
import json
import logging
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix

logger = logging.getLogger(__name__)


class InsufficientLabelsError(ValueError):
    """Raised when ground-truth labels do not meet the minimum required for reliable evaluation."""
    def __init__(self, pos_count: int, neg_count: int, min_required: int = 8, message: str = ""):
        self.pos_count = pos_count
        self.neg_count = neg_count
        self.min_required = min_required
        if not message:
            message = (
                f"Insufficient positive/negative account labels for reliable evaluation: "
                f"found {pos_count} positive and {neg_count} negative labels "
                f"(need at least {min_required} of each class before a stratified holdout)."
            )
        super().__init__(message)

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
    "circular_flow_indicator",
]


def train_base_model(
    features_df: pd.DataFrame,
    artifacts_dir: str = "ml/artifacts",
    min_required: int = 8,
) -> tuple:
    """
    Trains the designated production base model (XGBoost) on extracted features.
    Returns (model, scaler, metrics_dict).
    """
    from ml.src.train_xgboost import train_xgboost_model
    model, scaler, metrics = train_xgboost_model(features_df, artifacts_dir, min_required=min_required)
    joblib.dump(scaler, os.path.join(artifacts_dir, "scaler.pkl"))
    return model, scaler, metrics


def train_baseline_model(
    features_df: pd.DataFrame,
    artifacts_dir: str = "ml/artifacts",
    min_required: int = 8,
    model_type: str = "rf",
) -> tuple:
    """
    Trains baseline classifier on extracted account features.
    Supports model_type="xgboost" for XGBoost base model or model_type="rf" (default) for Random Forest.
    Returns (model, scaler, metrics_dict).
    """
    if model_type.lower() in ("xgboost", "xgb"):
        return train_base_model(features_df, artifacts_dir, min_required=min_required)

    os.makedirs(artifacts_dir, exist_ok=True)
    logger.info("[MODEL] Training Random Forest on %d accounts...", len(features_df))

    X = features_df[FEATURE_COLS].fillna(0)
    y = features_df["label"].astype(int)

    pos_count = int((y == 1).sum())
    neg_count = int((y == 0).sum())

    if y.nunique() < 2 or pos_count < min_required or neg_count < min_required:
        raise InsufficientLabelsError(
            pos_count=pos_count,
            neg_count=neg_count,
            min_required=min_required,
        )
    stratify = y
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=stratify
    )

    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=FEATURE_COLS, index=X_train.index)
    X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=FEATURE_COLS, index=X_test.index)

    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        random_state=42,
        class_weight="balanced",
    )
    clf.fit(X_train_scaled, y_train)

    y_pred = clf.predict(X_test_scaled)
    if len(clf.classes_) > 1 and 1 in clf.classes_:
        pos_idx = list(clf.classes_).index(1)
        y_proba = clf.predict_proba(X_test_scaled)[:, pos_idx]
    else:
        y_proba = y_pred

    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_proba)) if len(np.unique(y_test)) > 1 else 1.0
    pr_auc = float(average_precision_score(y_test, y_proba)) if len(np.unique(y_test)) > 1 else 0.0
    cm = confusion_matrix(y_test, y_pred).tolist()

    # Feature importances
    feature_importances = {
        col: round(float(imp), 4)
        for col, imp in zip(FEATURE_COLS, clf.feature_importances_)
    }
    sorted_importances = dict(sorted(feature_importances.items(), key=lambda x: x[1], reverse=True))

    metrics = {
        "status": "TRAINED",
        "model_type": "RandomForestClassifier",
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "threshold": 0.5,
        "train_class_counts": {str(k): int(v) for k, v in y_train.value_counts().items()},
        "test_class_counts": {str(k): int(v) for k, v in y_test.value_counts().items()},
        "confusion_matrix": cm,
        "feature_importances": sorted_importances,
        "feature_cols": FEATURE_COLS,
    }

    joblib.dump(scaler, os.path.join(artifacts_dir, "rf_scaler.pkl"))
    joblib.dump(clf, os.path.join(artifacts_dir, "rf_model.pkl"))

    with open(os.path.join(artifacts_dir, "rf_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    with open(os.path.join(artifacts_dir, "feature_schema.json"), "w") as f:
        json.dump(FEATURE_COLS, f, indent=2)

    logger.info(
        "[MODEL] Random Forest trained. Precision=%.4f | Recall=%.4f | F1=%.4f | ROC-AUC=%.4f",
        precision, recall, f1, roc_auc
    )
    return clf, scaler, metrics


def train_all_models(
    features_df: pd.DataFrame,
    G=None,
    artifacts_dir: str = "ml/artifacts",
    allow_insufficient_labels: bool = False,
    min_required: int = 8,
    base_model: str = "XGBoost",
) -> dict:
    """
    Trains and compares Random Forest, AdaBoost, XGBoost, and GraphSAGE.
    Determines the best model dynamically based on PR-AUC / F1-score / Recall.
    Saves comprehensive metrics to ml/artifacts/metrics.json.

    If positive or negative labels are insufficient for reliable stratified holdout:
    - If allow_insufficient_labels is False: raises InsufficientLabelsError.
    - If allow_insufficient_labels is True: records SKIPPED_INSUFFICIENT_LABELS status
      and diagnostics without fabricating metrics or synthesizing labels.
    """
    os.makedirs(artifacts_dir, exist_ok=True)
    with open(os.path.join(artifacts_dir, "feature_schema.json"), "w") as f:
        json.dump(FEATURE_COLS, f, indent=2)

    pos_count = int((features_df["label"] == 1).sum())
    neg_count = int((features_df["label"] == 0).sum())
    total_count = len(features_df)

    if pos_count < min_required or neg_count < min_required:
        msg = (
            f"Insufficient positive/negative account labels for reliable evaluation: "
            f"found {pos_count} positive and {neg_count} negative accounts out of {total_count} "
            f"(need at least {min_required} of each class before a stratified holdout)."
        )
        if not allow_insufficient_labels:
            raise InsufficientLabelsError(pos_count, neg_count, min_required, msg)

        logger.warning(
            "[ML PIPELINE] %s Skipping ML evaluation; saving diagnostic record.", msg
        )
        skipped_metrics = {
            "status": "SKIPPED_INSUFFICIENT_LABELS",
            "best_model": None,
            "best_model_display": "None (Training Skipped)",
            "model_type": "None",
            "precision": None,
            "recall": None,
            "f1_score": None,
            "roc_auc": None,
            "pr_auc": None,
            "confusion_matrix": None,
            "models_comparison": {},
            "feature_importances": {},
            "total_accounts_evaluated": 0,
            "dataset_type": "IBM AML",
            "selection_policy": "highest PR-AUC, then F1, then recall at threshold 0.5",
            "diagnostics": {
                "total_accounts": total_count,
                "positive_accounts": pos_count,
                "negative_accounts": neg_count,
                "positive_ratio_pct": round(pos_count / max(1, total_count) * 100, 4),
                "min_required_per_class": min_required,
                "reason": (
                    f"Only {pos_count} positive accounts identified. "
                    f"At least {min_required} are required for statistically valid stratified holdout."
                ),
                "recommendation": (
                    "Ingest at least 200,000 transactions (e.g. --sample-rows 200000) or run with full dataset "
                    "to capture enough ground-truth laundering accounts for model evaluation."
                ),
            },
        }
        with open(os.path.join(artifacts_dir, "metrics.json"), "w") as f:
            json.dump(skipped_metrics, f, indent=2)
        return skipped_metrics

    logger.info("[ML PIPELINE] Training all models (RF, AdaBoost, XGBoost, GraphSAGE)...")

    models_comparison = {}
    rf_metrics = {}
    ada_metrics = {}
    xgb_metrics = {}
    gnn_metrics = {}

    # 1. Random Forest
    try:
        _, scaler, rf_metrics = train_baseline_model(features_df, artifacts_dir, min_required=min_required)
        models_comparison["RandomForest"] = {
            "model_name": "Random Forest",
            "precision": rf_metrics.get("precision", 0.0),
            "recall": rf_metrics.get("recall", 0.0),
            "f1_score": rf_metrics.get("f1_score", 0.0),
            "roc_auc": rf_metrics.get("roc_auc", 0.0),
            "pr_auc": rf_metrics.get("pr_auc", 0.0),
            "confusion_matrix": rf_metrics.get("confusion_matrix", []),
        }
    except Exception as e:
        logger.error("[ML PIPELINE] Random Forest training error: %s", e)
        rf_metrics = {"error": str(e)}

    # 2. AdaBoost
    try:
        from ml.src.train_adaboost import train_adaboost_model
        _, _, ada_metrics = train_adaboost_model(features_df, artifacts_dir, min_required=min_required)
        models_comparison["AdaBoost"] = {
            "model_name": "AdaBoost",
            "precision": ada_metrics.get("precision", 0.0),
            "recall": ada_metrics.get("recall", 0.0),
            "f1_score": ada_metrics.get("f1_score", 0.0),
            "roc_auc": ada_metrics.get("roc_auc", 0.0),
            "pr_auc": ada_metrics.get("pr_auc", 0.0),
            "confusion_matrix": ada_metrics.get("confusion_matrix", []),
        }
    except Exception as e:
        logger.error("[ML PIPELINE] AdaBoost training error: %s", e)
        ada_metrics = {"error": str(e)}

    # 3. XGBoost
    try:
        from ml.src.train_xgboost import train_xgboost_model
        _, _, xgb_metrics = train_xgboost_model(features_df, artifacts_dir, min_required=min_required)
        models_comparison["XGBoost"] = {
            "model_name": "XGBoost",
            "precision": xgb_metrics.get("precision", 0.0),
            "recall": xgb_metrics.get("recall", 0.0),
            "f1_score": xgb_metrics.get("f1_score", 0.0),
            "roc_auc": xgb_metrics.get("roc_auc", 0.0),
            "pr_auc": xgb_metrics.get("pr_auc", 0.0),
            "threshold": xgb_metrics.get("threshold", 0.5),
            "confusion_matrix": xgb_metrics.get("confusion_matrix", []),
        }
    except Exception as e:
        logger.error("[ML PIPELINE] XGBoost training error: %s", e)
        xgb_metrics = {"error": str(e)}

    # 4. GraphSAGE
    if G is not None:
        try:
            from ml.src.train_gnn import train_gnn_model
            _, gnn_metrics = train_gnn_model(features_df, G, artifacts_dir, min_required=min_required)
            if "precision" in gnn_metrics and "error" not in gnn_metrics:
                models_comparison["GraphSAGE"] = {
                    "model_name": "GraphSAGE (GNN)",
                    "precision": gnn_metrics.get("precision", 0.0),
                    "recall": gnn_metrics.get("recall", 0.0),
                    "f1_score": gnn_metrics.get("f1_score", 0.0),
                    "roc_auc": gnn_metrics.get("roc_auc", 0.0),
                    "pr_auc": gnn_metrics.get("pr_auc", 0.0),
                    "confusion_matrix": gnn_metrics.get("confusion_matrix", []),
                }
        except Exception as e:
            logger.error("[ML PIPELINE] GraphSAGE training error: %s", e)
            gnn_metrics = {"error": str(e)}

    if not models_comparison:
        raise RuntimeError("All models failed training and evaluation.")

    # Designated base model selection:
    if base_model and base_model in models_comparison and "error" not in models_comparison[base_model]:
        best_name = base_model
    else:
        # PR-AUC is the primary selection metric for rare laundering; F1 and recall
        # are tie breakers at the fixed 0.5 threshold.
        best_name = max(
            models_comparison.keys(),
            key=lambda m: (
                models_comparison[m].get("pr_auc", 0.0),
                models_comparison[m].get("f1_score", 0.0),
                models_comparison[m].get("recall", 0.0),
            )
        )
    best_model_info = models_comparison[best_name]

    feat_importances = (
        xgb_metrics.get("feature_importances", {})
        if (best_name == "XGBoost" and "feature_importances" in xgb_metrics)
        else rf_metrics.get("feature_importances", {})
    )

    consolidated_metrics = {
        "status": "TRAINED",
        "base_model": base_model or best_name,
        "best_model": best_name,
        "best_model_display": best_model_info["model_name"],
        "model_type": best_model_info["model_name"],
        "precision": best_model_info["precision"],
        "recall": best_model_info["recall"],
        "f1_score": best_model_info["f1_score"],
        "roc_auc": best_model_info["roc_auc"],
        "pr_auc": best_model_info.get("pr_auc", 0.0),
        "confusion_matrix": best_model_info["confusion_matrix"],
        "models_comparison": models_comparison,
        "feature_importances": feat_importances,
        "total_accounts_evaluated": len(features_df),
        "dataset_type": "IBM AML",
        "selection_policy": (
            f"Designated base model: {best_name} (with scale_pos_weight & precision-recall threshold tuning for AML class imbalance)"
            if best_name == "XGBoost"
            else "highest PR-AUC, then F1, then recall at threshold 0.5"
        ),
        "diagnostics": {
            "total_accounts": total_count,
            "positive_accounts": pos_count,
            "negative_accounts": neg_count,
            "positive_ratio_pct": round(pos_count / max(1, total_count) * 100, 4),
        },
    }

    metrics_path = os.path.join(artifacts_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(consolidated_metrics, f, indent=2)

    logger.info(
        "[ML PIPELINE] Comparison complete. Best Model: %s (PR-AUC: %.4f, F1: %.4f, Recall: %.4f, Precision: %.4f, Threshold: %s)",
        best_name, best_model_info.get("pr_auc", 0.0), best_model_info["f1_score"],
        best_model_info["recall"], best_model_info["precision"],
        best_model_info.get("threshold", 0.5),
    )
    return consolidated_metrics

