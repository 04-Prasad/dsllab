"""
GraphGuard IBM AML Preprocessing Engine
=======================================
Implements robust chunked loading, cleaning, validation, account-level
aggregation, label derivation, and Parquet caching for the IBM AML dataset.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np

from config.settings import settings
from ml.src.ibm_adapter import (
    load_ibm_transactions,
    load_ibm_accounts,
    normalize_transaction_columns,
    normalize_account_columns,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CACHE_SCHEMA_VERSION = "ibm-preprocessing-v2"


def _cache_metadata(sample_rows: int) -> Dict[str, Any]:
    """Inputs which make a processed-data cache safe to reuse."""
    source = settings.ibm_transactions_path.resolve()
    source_stat = source.stat()
    accounts = settings.ibm_accounts_path.resolve()
    accounts_stat = accounts.stat()
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "source_path": str(source),
        "source_size": source_stat.st_size,
        "source_mtime_ns": source_stat.st_mtime_ns,
        "accounts_path": str(accounts),
        "accounts_size": accounts_stat.st_size,
        "accounts_mtime_ns": accounts_stat.st_mtime_ns,
        "sample_rows": int(sample_rows),
        "preprocessing": "drop_duplicate_timestamp_sender_receiver_amount;positive_amount;binary_label",
    }
    payload["key"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return payload


def preprocess_transactions(
    raw_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Cleans and validates the normalized IBM transaction DataFrame.

    Reports:
    - original row count
    - cleaned row count
    - removed rows
    - missing values
    - invalid timestamps
    - invalid amounts
    - duplicate count
    - laundering count
    - normal count
    """
    orig_count = len(raw_df)
    logger.info("[PREPROCESSING] Cleaning %d raw transactions...", orig_count)

    df = raw_df.copy()

    # 1. Enforce string account IDs (never numeric)
    df["sender_account_id"] = df["sender_account_id"].astype(str).str.strip()
    df["receiver_account_id"] = df["receiver_account_id"].astype(str).str.strip()
    df["sender_account"] = df["sender_account_id"]
    df["receiver_account"] = df["receiver_account_id"]

    # 2. Check and drop duplicate rows
    duplicate_count = int(df.duplicated(subset=["timestamp", "sender_account_id", "receiver_account_id", "amount"]).sum())
    if duplicate_count > 0:
        df = df.drop_duplicates(subset=["timestamp", "sender_account_id", "receiver_account_id", "amount"])

    # 3. Parse and validate timestamps
    raw_ts = df["timestamp"].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    invalid_ts_count = int(df["timestamp"].isna().sum())
    df = df.dropna(subset=["timestamp"])

    # 4. Parse and validate amounts
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    invalid_amt_count = int((df["amount"].isna() | (df["amount"] <= 0)).sum())
    df = df[df["amount"].notna() & (df["amount"] > 0)]

    # 5. Clean missing values in categorical fields
    if "payment_format" in df.columns:
        df["payment_format"] = df["payment_format"].fillna("UNKNOWN").astype(str).str.upper()
    else:
        df["payment_format"] = "TRANSFER"

    # 6. Validate target values
    if "is_laundering" in df.columns:
        df["is_laundering"] = (pd.to_numeric(df["is_laundering"], errors="coerce").fillna(0) == 1).astype(int)
    else:
        df["is_laundering"] = 0
    df["label"] = df["is_laundering"]

    # Ensure transaction_id
    if "transaction_id" not in df.columns:
        df["transaction_id"] = [f"TX{i+1:08d}" for i in range(len(df))]

    cleaned_count = len(df)
    removed_count = orig_count - cleaned_count
    laundering_count = int((df["is_laundering"] == 1).sum())
    normal_count = int((df["is_laundering"] == 0).sum())

    stats = {
        "original_rows": orig_count,
        "cleaned_rows": cleaned_count,
        "removed_rows": removed_count,
        "duplicate_rows": duplicate_count,
        "invalid_timestamps": invalid_ts_count,
        "invalid_amounts": invalid_amt_count,
        "laundering_transactions": laundering_count,
        "normal_transactions": normal_count,
        "laundering_ratio_pct": round((laundering_count / cleaned_count * 100), 4) if cleaned_count > 0 else 0.0,
    }

    logger.info(
        "[PREPROCESSING] Summary: Original=%d | Cleaned=%d | Removed=%d | Laundering=%d (%.4f%%)",
        orig_count, cleaned_count, removed_count, laundering_count, stats["laundering_ratio_pct"]
    )

    return df, stats


def compute_label_diagnostics(tx_df: pd.DataFrame, acc_df: pd.DataFrame) -> Dict[str, Any]:
    """Generates detailed label and class balance diagnostics for pipeline reporting."""
    pos_tx = int((tx_df["is_laundering"] == 1).sum()) if "is_laundering" in tx_df.columns else 0
    total_tx = len(tx_df)
    neg_tx = total_tx - pos_tx

    pos_acc = int((acc_df["label"] == 1).sum()) if "label" in acc_df.columns else 0
    total_acc = len(acc_df)
    neg_acc = total_acc - pos_acc

    return {
        "transactions": {
            "total": total_tx,
            "positive_laundering": pos_tx,
            "negative_normal": neg_tx,
            "laundering_pct": round(pos_tx / max(1, total_tx) * 100, 4),
        },
        "accounts": {
            "total": total_acc,
            "positive_suspicious": pos_acc,
            "negative_legitimate": neg_acc,
            "suspicious_pct": round(pos_acc / max(1, total_acc) * 100, 4),
        },
        "sufficient_for_stratified_evaluation": pos_acc >= 8 and neg_acc >= 8,
        "min_required_positives": 8,
    }


def build_accounts_from_transactions(
    tx_df: pd.DataFrame,
    accounts_metadata_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Derives the complete account-level dataset from transaction participants,
    integrating metadata from LI-Small_accounts.csv if provided.

    Account Label Strategy:
    - account_label = 1 if the account participates as sender OR receiver
      in at least one transaction where is_laundering == 1.
    - account_label = 0 otherwise.

    Note: This binary label represents the ground-truth target for supervised
    learning and is strictly segregated from input feature calculations to prevent leakage.
    """
    logger.info("[PREPROCESSING] Deriving account dataset from transaction activity...")

    senders = set(tx_df["sender_account_id"].astype(str).str.strip().unique())
    receivers = set(tx_df["receiver_account_id"].astype(str).str.strip().unique())
    all_account_ids = sorted(list(senders.union(receivers)))

    # Identify accounts participating in laundering transactions
    laundering_txs = tx_df[tx_df["is_laundering"] == 1]
    laundering_senders = set(laundering_txs["sender_account_id"].astype(str).str.strip().unique())
    laundering_receivers = set(laundering_txs["receiver_account_id"].astype(str).str.strip().unique())
    suspicious_accounts = laundering_senders.union(laundering_receivers)

    logger.info(
        "[PREPROCESSING] Total active accounts: %d | Suspicious accounts (involved in laundering): %d",
        len(all_account_ids), len(suspicious_accounts)
    )

    # Calculate account first/last activity timestamp
    min_send = tx_df.groupby("sender_account_id")["timestamp"].min()
    min_recv = tx_df.groupby("receiver_account_id")["timestamp"].min()
    combined_min = pd.concat([min_send, min_recv]).groupby(level=0).min()

    acc_rows = []
    metadata_map = {}
    if accounts_metadata_df is not None and not accounts_metadata_df.empty:
        # The IBM account file can contain hundreds of thousands of dormant
        # accounts. Keep metadata only for transaction participants before
        # constructing a Python dictionary, avoiding an unnecessary memory spike.
        active_metadata = accounts_metadata_df[
            accounts_metadata_df["account_id"].astype(str).isin(all_account_ids)
        ]
        dedup_acc = active_metadata.drop_duplicates(subset=["account_id"])
        metadata_map = dedup_acc.set_index("account_id").to_dict(orient="index")

    for acc_id in all_account_ids:
        meta = metadata_map.get(acc_id, {})
        first_tx = combined_min.get(acc_id, tx_df["timestamp"].min())
        acc_rows.append({
            "account_id": str(acc_id),
            "account_created_at": str(first_tx),
            "account_type": meta.get("account_type", "CURRENT"),
            "bank_name": meta.get("bank_name", "UNKNOWN"),
            "bank_id": str(meta.get("bank_id", "")),
            "entity_name": meta.get("entity_name", "UNKNOWN"),
            "status": "ACTIVE",
            "label": 1 if acc_id in suspicious_accounts else 0,
        })

    acc_df = pd.DataFrame(acc_rows)
    return acc_df


def run_ibm_preprocessing(
    sample_rows: int = 0,
    force_recompute: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Executes the complete preprocessing pipeline:
    1. Checks Parquet cache (if enabled and force_recompute=False)
    2. Reads and normalizes LI-Small_Trans.csv and LI-Small_accounts.csv
    3. Cleans data and generates summary statistics
    4. Caches processed DataFrames to Parquet
    """
    settings.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    tx_parquet = settings.processed_transactions_parquet
    acc_parquet = settings.processed_accounts_parquet
    metadata_path = settings.PROCESSED_DATA_DIR / "cache_metadata.json"
    settings.validate_ibm_files()
    effective_sample = sample_rows if sample_rows > 0 else settings.IBM_SAMPLE_ROWS
    requested_metadata = _cache_metadata(effective_sample)

    # Check cache
    cache_valid = False
    if tx_parquet.exists() and acc_parquet.exists() and metadata_path.exists():
        try:
            cache_valid = json.loads(metadata_path.read_text(encoding="utf-8")).get("key") == requested_metadata["key"]
        except (OSError, ValueError):
            cache_valid = False
    if settings.USE_PARQUET_CACHE and not force_recompute and cache_valid:
        logger.info("[IBM PREPROCESSING] Loading cached processed Parquet files from %s...", settings.PROCESSED_DATA_DIR)
        tx_df = pd.read_parquet(tx_parquet)
        acc_df = pd.read_parquet(acc_parquet)
        # Ensure account IDs are string
        tx_df["sender_account_id"] = tx_df["sender_account_id"].astype(str)
        tx_df["receiver_account_id"] = tx_df["receiver_account_id"].astype(str)
        acc_df["account_id"] = acc_df["account_id"].astype(str)
        stats = {
            "cached": True,
            "cache_status": "hit",
            "source_file": settings.ibm_transactions_path.name,
            "requested_rows": effective_sample,
            "loaded_rows": len(tx_df),
            "cleaned_rows": len(tx_df),
            "total_transactions": len(tx_df),
            "total_accounts": len(acc_df),
            "laundering_transactions": int((tx_df["is_laundering"] == 1).sum()),
            "suspicious_accounts": int((acc_df["label"] == 1).sum()),
            "legitimate_accounts": len(acc_df) - int((acc_df["label"] == 1).sum()),
            "laundering_ratio_pct": round(int((tx_df["is_laundering"] == 1).sum()) / max(1, len(tx_df)) * 100, 4),
            "suspicious_account_ratio_pct": round(int((acc_df["label"] == 1).sum()) / max(1, len(acc_df)) * 100, 4),
            "diagnostics": compute_label_diagnostics(tx_df, acc_df),
        }
        return tx_df, acc_df, stats
    if settings.USE_PARQUET_CACHE and not force_recompute:
        logger.info("[IBM PREPROCESSING] Cache miss: source, row limit, schema, or preprocessing configuration changed.")
    elif force_recompute:
        logger.info("[IBM PREPROCESSING] Cache bypassed by --force-recompute.")
    logger.info("[IBM DATA] Loading transactions from %s (sample=%d)...", settings.ibm_transactions_path, effective_sample)
    raw_tx = load_ibm_transactions(settings.ibm_transactions_path, sample_rows=effective_sample)

    logger.info("[IBM DATA] Loading accounts metadata from %s...", settings.ibm_accounts_path)
    raw_acc = load_ibm_accounts(settings.ibm_accounts_path)

    # Clean transactions
    tx_df, stats = preprocess_transactions(raw_tx)

    # Build account dataset
    acc_df = build_accounts_from_transactions(tx_df, raw_acc)

    # Save to Parquet cache
    if settings.USE_PARQUET_CACHE:
        logger.info("[IBM PREPROCESSING] Caching processed DataFrames to Parquet: %s and %s", tx_parquet, acc_parquet)
        tx_df.to_parquet(tx_parquet, index=False)
        acc_df.to_parquet(acc_parquet, index=False)
        metadata_path.write_text(json.dumps(requested_metadata, indent=2), encoding="utf-8")

    stats["total_accounts"] = len(acc_df)
    stats["suspicious_accounts"] = int((acc_df["label"] == 1).sum())
    stats["legitimate_accounts"] = len(acc_df) - stats["suspicious_accounts"]
    stats["suspicious_account_ratio_pct"] = round(stats["suspicious_accounts"] / max(1, len(acc_df)) * 100, 4)
    stats["cached"] = False
    stats["cache_status"] = "forced-rebuild" if force_recompute else "miss"
    stats["source_file"] = settings.ibm_transactions_path.name
    stats["requested_rows"] = effective_sample
    stats["loaded_rows"] = len(raw_tx)
    stats["diagnostics"] = compute_label_diagnostics(tx_df, acc_df)

    return tx_df, acc_df, stats


if __name__ == "__main__":
    tx, acc, st = run_ibm_preprocessing(sample_rows=50000)
    print("Preprocessing completed successfully!")
    print(st)
