"""
GraphGuard Models & Evaluation API Routes
=========================================
Exposes trained model performance metrics, comparison between Random Forest,
AdaBoost, XGBoost, and GraphSAGE, feature importances, and confusion matrices.
"""

import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from config.settings import settings

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("/metrics")
def get_model_metrics():
    """
    Returns the latest trained model metrics, including comparison between
    Random Forest, AdaBoost, and GraphSAGE, best model, and confusion matrices.
    """
    metrics_path = settings.ML_ARTIFACTS_DIR / "metrics.json"
    if not metrics_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Model metrics not found. Run the training pipeline first.",
        )

    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read metrics: {str(e)}")


@router.get("/comparison")
def get_model_comparison():
    """Returns side-by-side comparison of all evaluated AML models."""
    metrics_path = settings.ML_ARTIFACTS_DIR / "metrics.json"
    if not metrics_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Model metrics not found. Run the training pipeline first.",
        )

    with open(metrics_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "status": data.get("status", "TRAINED"),
        "base_model": data.get("base_model", "XGBoost"),
        "best_model": data.get("best_model", "XGBoost"),
        "best_model_display": data.get("best_model_display") or ("None" if not data.get("best_model") else "XGBoost"),
        "models": data.get("models_comparison", {}),
        "diagnostics": data.get("diagnostics", {}),
    }


@router.get("/base")
def get_base_model():
    """
    Returns detailed metrics, hyper-parameters, and threshold tuning
    for the primary base model (XGBoost).
    """
    xgb_metrics_path = settings.ML_ARTIFACTS_DIR / "xgboost_metrics.json"
    if xgb_metrics_path.exists():
        try:
            with open(xgb_metrics_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read XGBoost metrics: {str(e)}")
    return get_model_metrics()


@router.get("/features")
def get_feature_schema():
    """Returns the list of features used across tabular and graph models."""
    schema_path = settings.ML_ARTIFACTS_DIR / "feature_schema.json"
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            return {"features": json.load(f)}
    return {"features": []}


@router.get("/xgboost")
def get_xgboost_metrics():
    """
    Returns detailed training metadata, scale_pos_weight, validation threshold tuning,
    and operational false-positive burden analysis for the XGBoost model.
    """
    xgb_metrics_path = settings.ML_ARTIFACTS_DIR / "xgboost_metrics.json"
    if not xgb_metrics_path.exists():
        raise HTTPException(
            status_code=404,
            detail="XGBoost model metrics not found. Train the model first.",
        )
    try:
        with open(xgb_metrics_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read XGBoost metrics: {str(e)}")

