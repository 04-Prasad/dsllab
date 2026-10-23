"""
GraphGuard XGBoost ML Model Trainer
====================================
Trains an XGBoost binary classifier on extracted account features with:
- scale_pos_weight for class imbalance handling (training only)
- Validation-based early stopping
- Threshold tuning on held-out validation set (not test set)
- Comprehensive evaluation metrics (Precision, Recall, F1, ROC-AUC, PR-AUC, Confusion Matrix)
- Reproducible seeds and versioned artifact saving

Label definition:
    label=1 → suspicious (account involved in laundering transaction)
    label=0 → legitimate
"""

import os
import json
import logging
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
)

from ml.src.train_baseline import FEATURE_COLS, InsufficientLabelsError

logger = logging.getLogger(__name__)

# ── Default XGBoost hyperparameters ──────────────────────────────────────────
# These are reasonable defaults for a highly imbalanced binary classification
# task. All parameters are configurable via the train function arguments.
DEFAULT_XGBOOST_PARAMS = {
    "n_estimators": 500,          # max boosting rounds (early stopping controls actual count)
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "gamma": 0.1,
    "reg_alpha": 0.1,             # L1 regularization
    "reg_lambda": 1.0,            # L2 regularization
    "random_state": 42,
    "n_jobs": -1,
    "eval_metric": "logloss",
}

# ── Early stopping configuration ─────────────────────────────────────────────
EARLY_STOPPING_ROUNDS = 30


def _compute_scale_pos_weight(y_train: np.ndarray) -> float:
    """
    Calculates scale_pos_weight from TRAINING labels only.

    Formula: scale_pos_weight = count(negative) / count(positive)

    This instructs XGBoost to weight positive-class errors more heavily,
    compensating for severe class imbalance without resampling.
    """
    pos_count = int((y_train == 1).sum())
    neg_count = int((y_train == 0).sum())
    if pos_count == 0:
        logger.warning("[XGBOOST] No positive samples in training set; scale_pos_weight set to 1.0")
        return 1.0
    weight = neg_count / pos_count
    logger.info(
        "[XGBOOST] scale_pos_weight = %d / %d = %.2f",
        neg_count, pos_count, weight,
    )
    return weight


def _tune_threshold_on_validation(
    y_val: np.ndarray,
    y_val_proba: np.ndarray,
    min_recall: float = 0.90,
) -> dict:
    """
    Selects an operating threshold using VALIDATION data only.

    Strategy: Among all thresholds achieving >= min_recall on the positive class,
    select the one that maximises precision (i.e. minimises false positives while
    maintaining the recall floor). This reflects an AML operational objective where
    missing suspicious activity is costly, but overwhelming analysts with false
    positives is also unacceptable.

    If no threshold achieves the recall floor, the threshold maximising F1 is used
    as a fallback.

    Returns a dict with threshold, rationale, and validation metrics at that threshold.
    """
    precisions, recalls, thresholds = precision_recall_curve(y_val, y_val_proba)
    # precision_recall_curve returns arrays of length n+1 for precision/recall
    # and n for thresholds; the last precision/recall entry corresponds to
    # recall=0, precision=1, which has no threshold.

    best_threshold = 0.5
    rationale = "default"

    # Candidate thresholds where recall >= min_recall
    valid_mask = recalls[:-1] >= min_recall
    if valid_mask.any():
        # Among valid candidates, pick the one with highest precision
        candidate_precisions = precisions[:-1][valid_mask]
        candidate_thresholds = thresholds[valid_mask]
        best_idx = np.argmax(candidate_precisions)
        best_threshold = float(candidate_thresholds[best_idx])
        rationale = (
            f"Maximise precision subject to recall >= {min_recall:.0%} on validation set. "
            f"Achieved precision={float(candidate_precisions[best_idx]):.4f} at recall >= {min_recall:.0%}."
        )
    else:
        # Fallback: maximise F1
        f1_scores = 2 * (precisions[:-1] * recalls[:-1]) / (
            precisions[:-1] + recalls[:-1] + 1e-10
        )
        best_idx = np.argmax(f1_scores)
        best_threshold = float(thresholds[best_idx])
        rationale = (
            f"No threshold achieved recall >= {min_recall:.0%}. "
            f"Fell back to maximum F1={float(f1_scores[best_idx]):.4f} on validation set."
        )

    # Compute validation metrics at chosen threshold
    val_pred = (y_val_proba >= best_threshold).astype(int)
    val_precision = float(precision_score(y_val, val_pred, zero_division=0))
    val_recall = float(recall_score(y_val, val_pred, zero_division=0))
    val_f1 = float(f1_score(y_val, val_pred, zero_division=0))
    val_flagged = int(val_pred.sum())
    val_total = len(y_val)

    return {
        "threshold": round(best_threshold, 6),
        "rationale": rationale,
        "min_recall_target": min_recall,
        "validation_precision": round(val_precision, 4),
        "validation_recall": round(val_recall, 4),
        "validation_f1": round(val_f1, 4),
        "validation_flagged": val_flagged,
        "validation_total": val_total,
        "validation_flagged_pct": round(val_flagged / max(1, val_total) * 100, 4),
    }


def train_xgboost_model(
    features_df: pd.DataFrame,
    artifacts_dir: str = "ml/artifacts",
    min_required: int = 8,
    xgb_params: dict | None = None,
    early_stopping_rounds: int = EARLY_STOPPING_ROUNDS,
    min_recall_target: float = 0.90,
) -> tuple:
    """
    Trains an XGBoost binary classifier on extracted account features.

    Split strategy:
        - Train: 60% (used for gradient boosting)
        - Validation: 15% (used for early stopping + threshold tuning)
        - Test: 25% (held out, evaluated once)

    The test split uses the same random_state=42 and test_size=0.25 as the
    existing RF/AdaBoost/GNN models, ensuring comparable evaluation.

    Returns (model, scaler, metrics_dict).
    """
    try:
        import xgboost as xgb
    except ImportError:
        raise ImportError(
            "xgboost is not installed. Install it with: pip install xgboost"
        )

    os.makedirs(artifacts_dir, exist_ok=True)
    logger.info("[XGBOOST] Training XGBoost on %d accounts...", len(features_df))

    X = features_df[FEATURE_COLS].fillna(0)
    y = features_df["label"].astype(int)

    pos_count_all = int((y == 1).sum())
    neg_count_all = int((y == 0).sum())

    # ── Guard: sufficient labels ─────────────────────────────────────────────
    if y.nunique() < 2 or pos_count_all < min_required or neg_count_all < min_required:
        raise InsufficientLabelsError(
            pos_count=pos_count_all,
            neg_count=neg_count_all,
            min_required=min_required,
        )

    # ── Step 1: Split into train_val (75%) and test (25%) ────────────────────
    # This produces the SAME test set as existing models (random_state=42,
    # test_size=0.25, stratify=y).
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y,
    )

    # ── Step 2: Split train_val into train (80% of 75% = 60%) and val (20% of 75% = 15%) ─
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=0.20, random_state=42, stratify=y_train_val,
    )

    logger.info(
        "[XGBOOST] Split sizes — Train: %d (pos=%d) | Val: %d (pos=%d) | Test: %d (pos=%d)",
        len(y_train), int((y_train == 1).sum()),
        len(y_val), int((y_val == 1).sum()),
        len(y_test), int((y_test == 1).sum()),
    )

    # ── Step 3: Scale features ───────────────────────────────────────────────
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(
        scaler.fit_transform(X_train), columns=FEATURE_COLS, index=X_train.index,
    )
    X_val_scaled = pd.DataFrame(
        scaler.transform(X_val), columns=FEATURE_COLS, index=X_val.index,
    )
    X_test_scaled = pd.DataFrame(
        scaler.transform(X_test), columns=FEATURE_COLS, index=X_test.index,
    )
    joblib.dump(scaler, os.path.join(artifacts_dir, "xgboost_scaler.pkl"))

    # ── Step 4: Compute scale_pos_weight from training labels ────────────────
    scale_pos_weight = _compute_scale_pos_weight(y_train.values)

    # ── Step 5: Configure and train XGBoost ──────────────────────────────────
    params = {**DEFAULT_XGBOOST_PARAMS}
    if xgb_params:
        params.update(xgb_params)
    params["scale_pos_weight"] = scale_pos_weight
    if early_stopping_rounds and early_stopping_rounds > 0:
        params["early_stopping_rounds"] = early_stopping_rounds

    clf = xgb.XGBClassifier(
        **params,
        verbosity=0,
    )

    # Early stopping on validation set
    clf.fit(
        X_train_scaled, y_train,
        eval_set=[(X_val_scaled, y_val)],
        verbose=False,
    )

    best_iteration = getattr(clf, "best_iteration", params["n_estimators"])
    logger.info("[XGBOOST] Training stopped at iteration %d", best_iteration)

    # ── Step 6: Tune threshold on validation set ─────────────────────────────
    y_val_proba = clf.predict_proba(X_val_scaled)[:, 1]
    threshold_info = _tune_threshold_on_validation(
        y_val.values, y_val_proba, min_recall=min_recall_target,
    )
    chosen_threshold = threshold_info["threshold"]
    logger.info(
        "[XGBOOST] Chosen threshold=%.4f | Rationale: %s",
        chosen_threshold, threshold_info["rationale"],
    )

    # ── Step 7: Evaluate on held-out test set (one-time) ─────────────────────
    y_test_proba = clf.predict_proba(X_test_scaled)[:, 1]
    y_test_pred = (y_test_proba >= chosen_threshold).astype(int)

    precision = float(precision_score(y_test, y_test_pred, zero_division=0))
    recall = float(recall_score(y_test, y_test_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_test_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_test_proba)) if len(np.unique(y_test)) > 1 else 1.0
    pr_auc = float(average_precision_score(y_test, y_test_proba)) if len(np.unique(y_test)) > 1 else 0.0
    cm = confusion_matrix(y_test, y_test_pred).tolist()

    # Decode confusion matrix at chosen threshold
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
    test_flagged = int(y_test_pred.sum())
    test_total = len(y_test)
    test_pos = int((y_test == 1).sum())
    test_neg = int((y_test == 0).sum())
    test_prevalence = round(test_pos / max(1, test_total) * 100, 4)

    # Also compute at default threshold 0.5 for direct apples-to-apples comparison with other models
    y_test_pred_05 = (y_test_proba >= 0.5).astype(int)
    cm_05 = confusion_matrix(y_test, y_test_pred_05).tolist()
    metrics_at_05 = {
        "threshold": 0.5,
        "precision": round(float(precision_score(y_test, y_test_pred_05, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_test_pred_05, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_test, y_test_pred_05, zero_division=0)), 4),
        "confusion_matrix": cm_05,
        "confusion_matrix_labels": {
            "TN": cm_05[0][0], "FP": cm_05[0][1], "FN": cm_05[1][0], "TP": cm_05[1][1]
        },
        "flagged_count": int(y_test_pred_05.sum()),
        "flagged_pct": round(int(y_test_pred_05.sum()) / max(1, test_total) * 100, 4),
    }

    # Feature importances
    feature_importances = {}
    try:
        importances = clf.feature_importances_
        feature_importances = {
            col: round(float(imp), 4)
            for col, imp in zip(FEATURE_COLS, importances)
        }
        feature_importances = dict(
            sorted(feature_importances.items(), key=lambda x: x[1], reverse=True)
        )
    except Exception:
        pass

    # ── Step 8: Build comprehensive metrics ──────────────────────────────────
    xgb_version = xgb.__version__

    metrics = {
        "status": "TRAINED",
        "model_type": "XGBClassifier",
        "xgboost_version": xgb_version,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "threshold": chosen_threshold,
        "metrics_at_default_threshold": metrics_at_05,
        "threshold_tuning": threshold_info,
        "confusion_matrix": cm,
        "confusion_matrix_labels": {"TN": tn, "FP": fp, "FN": fn, "TP": tp},
        "test_flagged_count": test_flagged,
        "test_flagged_pct": round(test_flagged / max(1, test_total) * 100, 4),
        "test_prevalence_pct": test_prevalence,
        "train_class_counts": {str(k): int(v) for k, v in y_train.value_counts().items()},
        "val_class_counts": {str(k): int(v) for k, v in y_val.value_counts().items()},
        "test_class_counts": {str(k): int(v) for k, v in y_test.value_counts().items()},
        "scale_pos_weight": round(scale_pos_weight, 2),
        "best_iteration": best_iteration,
        "early_stopping_rounds": early_stopping_rounds,
        "feature_importances": feature_importances,
        "feature_cols": FEATURE_COLS,
        "xgb_params": {k: v for k, v in params.items() if k != "scale_pos_weight"},
        "operational_analysis": {
            "false_positive_burden": (
                f"{fp} false alerts out of {test_neg} legitimate accounts "
                f"({round(fp / max(1, test_neg) * 100, 4)}% false alarm rate). "
                f"An analyst reviewing all flagged accounts would encounter "
                f"{fp} false alerts for every {tp} true detection."
            ),
            "missed_detections": (
                f"{fn} suspicious accounts missed out of {test_pos} total "
                f"({round(fn / max(1, test_pos) * 100, 2)}% miss rate)."
            ),
        },
    }

    # ── Step 9: Save artifacts ───────────────────────────────────────────────
    # Save model in JSON format (version-portable, recommended by XGBoost docs)
    model_path = os.path.join(artifacts_dir, "xgboost_model.json")
    clf.save_model(model_path)

    # Also save as pkl for compatibility with the existing joblib-based loading pattern
    joblib.dump(clf, os.path.join(artifacts_dir, "xgboost_model.pkl"))

    metrics_path = os.path.join(artifacts_dir, "xgboost_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logger.info(
        "[XGBOOST] XGBoost trained. Precision=%.4f | Recall=%.4f | F1=%.4f | "
        "ROC-AUC=%.4f | PR-AUC=%.4f | Threshold=%.4f",
        precision, recall, f1, roc_auc, pr_auc, chosen_threshold,
    )

    return clf, scaler, metrics
