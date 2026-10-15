"""
GraphGuard AdaBoost ML Model Trainer
====================================
Trains AdaBoost classifier on extracted account features with class balancing.
Computes evaluation metrics (Precision, Recall, F1, ROC-AUC, Confusion Matrix)
and saves model artifacts.
"""

import os
import json
import logging
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import AdaBoostClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix

from ml.src.train_baseline import FEATURE_COLS, InsufficientLabelsError

logger = logging.getLogger(__name__)


def train_adaboost_model(
    features_df: pd.DataFrame,
    artifacts_dir: str = "ml/artifacts",
    min_required: int = 8,
) -> tuple:
    """
    Trains AdaBoost on extracted account features.
    Returns (model, scaler, metrics_dict).
    """
    os.makedirs(artifacts_dir, exist_ok=True)
    logger.info("[MODEL] Training AdaBoost on %d accounts...", len(features_df))

    X = features_df[FEATURE_COLS].fillna(0)
    y = features_df["label"].astype(int)

    pos_count_all = int((y == 1).sum())
    neg_count_all = int((y == 0).sum())

    # Stratified train/test split
    if y.nunique() < 2 or pos_count_all < min_required or neg_count_all < min_required:
        raise InsufficientLabelsError(
            pos_count=pos_count_all,
            neg_count=neg_count_all,
            min_required=min_required,
        )
    stratify = y
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=stratify
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=FEATURE_COLS, index=X_train.index)
    X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=FEATURE_COLS, index=X_test.index)
    joblib.dump(scaler, os.path.join(artifacts_dir, "adaboost_scaler.pkl"))

    # Handle class imbalance in base estimator
    pos_count = (y_train == 1).sum()
    neg_count = (y_train == 0).sum()
    sample_weight = np.ones(len(y_train))
    if pos_count > 0 and neg_count > 0:
        weight_pos = neg_count / pos_count
        sample_weight[y_train == 1] = weight_pos

    base_estimator = DecisionTreeClassifier(max_depth=3, random_state=42)
    clf = AdaBoostClassifier(
        estimator=base_estimator,
        n_estimators=100,
        learning_rate=0.5,
        random_state=42,
    )
    clf.fit(X_train_scaled, y_train, sample_weight=sample_weight)

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

    metrics = {
        "status": "TRAINED",
        "model_type": "AdaBoostClassifier",
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "threshold": 0.5,
        "train_class_counts": {str(k): int(v) for k, v in y_train.value_counts().items()},
        "test_class_counts": {str(k): int(v) for k, v in y_test.value_counts().items()},
        "confusion_matrix": cm,
        "feature_cols": FEATURE_COLS,
    }

    joblib.dump(clf, os.path.join(artifacts_dir, "adaboost_model.pkl"))
    with open(os.path.join(artifacts_dir, "adaboost_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info(
        "[MODEL] AdaBoost trained successfully. Precision=%.4f | Recall=%.4f | F1=%.4f | ROC-AUC=%.4f",
        precision, recall, f1, roc_auc
    )

    return clf, scaler, metrics
