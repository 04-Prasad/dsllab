"""
GraphGuard IBM AML Data Adapter
================================
Normalizes raw IBM Transaction / Account CSV column names into the
GraphGuard internal schema.

IBM raw column reality (what pandas actually produces due to duplicate
column names in the CSV):
    Timestamp, From Bank, Account, To Bank, Account.1,
    Amount Received, Receiving Currency, Amount Paid,
    Payment Currency, Payment Format, Is Laundering

GraphGuard internal schema produced by this adapter:
    timestamp, sender_bank, sender_account, receiver_bank,
    receiver_account, amount_received, receiving_currency,
    amount (= Amount Paid), payment_currency, payment_format,
    is_laundering

IMPORTANT:
- sender_account and receiver_account are ALWAYS loaded / stored as strings.
- is_laundering is the TARGET label -- it must NOT be used as an ML input feature.
- The adapter does NOT modify the raw files.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── Column name mapping from IBM raw → GraphGuard internal ────────────────────

IBM_TRANSACTION_COLUMN_MAP = {
    "Timestamp": "timestamp",
    "From Bank": "sender_bank",
    "Account": "sender_account",      # first Account column (pandas default)
    "To Bank": "receiver_bank",
    "Account.1": "receiver_account",  # second Account column (pandas renames)
    "Amount Received": "amount_received",
    "Receiving Currency": "receiving_currency",
    "Amount Paid": "amount",          # primary monetary amount
    "Payment Currency": "payment_currency",
    "Payment Format": "payment_format",
    "Is Laundering": "is_laundering",
}

IBM_ACCOUNT_COLUMN_MAP = {
    "Bank Name": "bank_name",
    "Bank ID": "bank_id",
    "Account Number": "account_id",   # align with GraphGuard account_id
    "Entity ID": "entity_id",
    "Entity Name": "entity_name",
}

# Columns that must remain strings (no numeric coercion)
STRING_COLS = {"sender_account", "receiver_account", "sender_bank", "receiver_bank",
               "account_id", "bank_id", "entity_id"}

# Columns to convert to float
NUMERIC_COLS = {"amount", "amount_received"}


def normalize_transaction_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename IBM transaction CSV columns to GraphGuard internal schema.

    This function is safe with both:
    - Raw column names from pandas (with Account.1)
    - Already-renamed columns (idempotent)

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with IBM raw column names (or a subset thereof).

    Returns
    -------
    pd.DataFrame
        DataFrame with GraphGuard internal column names.
    """
    # Build rename map only for columns that actually exist in this df
    rename_map = {k: v for k, v in IBM_TRANSACTION_COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # Enforce string types for account/bank ID columns
    for col in STRING_COLS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Convert numeric amount columns
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Convert is_laundering to binary int strictly in {0, 1}
    if "is_laundering" in df.columns:
        raw_target = df["is_laundering"]
        if pd.api.types.is_numeric_dtype(raw_target):
            df["is_laundering"] = (raw_target == 1).astype(int)
        else:
            s = raw_target.astype(str).str.strip().str.lower()
            df["is_laundering"] = s.isin({"1", "true", "1.0"}).astype(int)
        df["label"] = df["is_laundering"]

    # Provide both sender_account and sender_account_id aliases for maximum interoperability
    if "sender_account" in df.columns and "sender_account_id" not in df.columns:
        df["sender_account_id"] = df["sender_account"]
    elif "sender_account_id" in df.columns and "sender_account" not in df.columns:
        df["sender_account"] = df["sender_account_id"]

    if "receiver_account" in df.columns and "receiver_account_id" not in df.columns:
        df["receiver_account_id"] = df["receiver_account"]
    elif "receiver_account_id" in df.columns and "receiver_account" not in df.columns:
        df["receiver_account"] = df["receiver_account_id"]

    # Provide synthetic-compatible transaction_id if missing
    if "transaction_id" not in df.columns:
        df["transaction_id"] = [f"TX{i+1:08d}" for i in range(len(df))]

    return df


def normalize_account_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename IBM account CSV columns to GraphGuard internal schema.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with IBM accounts raw column names.

    Returns
    -------
    pd.DataFrame
        DataFrame with GraphGuard internal column names.
    """
    rename_map = {k: v for k, v in IBM_ACCOUNT_COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # Enforce string types
    for col in ["account_id", "bank_id", "entity_id"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    if "status" not in df.columns:
        df["status"] = "ACTIVE"
    if "account_type" not in df.columns:
        df["account_type"] = "CURRENT"
    if "account_created_at" not in df.columns:
        df["account_created_at"] = ""

    return df


def load_ibm_transactions(
    path: Path,
    sample_rows: int = 0,
    usecols: Optional[list] = None,
    dtype_overrides: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Load IBM transaction CSV and immediately normalize to internal schema.

    Account ID columns are always loaded as str to prevent numeric coercion.

    Parameters
    ----------
    path : Path
        Path to LI-Small_Trans.csv.
    sample_rows : int
        If > 0, load only this many rows (for development / testing).
    usecols : list, optional
        Subset of IBM raw column names to load.
    dtype_overrides : dict, optional
        Additional dtype overrides for pd.read_csv.

    Returns
    -------
    pd.DataFrame
        Normalized transaction DataFrame.
    """
    # Always force account columns to str to prevent scientific notation / int coercion
    dtype = {
        "Account": str,
        "Account.1": str,
        "From Bank": str,
        "To Bank": str,
        "Is Laundering": str,
    }
    if dtype_overrides:
        dtype.update(dtype_overrides)

    kwargs = dict(
        filepath_or_buffer=str(path),
        dtype=dtype,
        low_memory=False,
    )
    if sample_rows > 0:
        kwargs["nrows"] = sample_rows
    if usecols:
        kwargs["usecols"] = usecols

    logger.info("[IBM ADAPTER] Loading transactions from %s ...", path)
    df = pd.read_csv(**kwargs)
    logger.info("[IBM ADAPTER] Loaded %d rows, columns: %s", len(df), list(df.columns))

    df = normalize_transaction_columns(df)
    logger.info("[IBM ADAPTER] Normalized to internal schema: %s", list(df.columns))
    return df


def load_ibm_accounts(path: Path) -> pd.DataFrame:
    """
    Load IBM accounts CSV and normalize to internal schema.

    Parameters
    ----------
    path : Path
        Path to LI-Small_accounts.csv.

    Returns
    -------
    pd.DataFrame
        Normalized accounts DataFrame with account_id as string.
    """
    logger.info("[IBM ADAPTER] Loading accounts from %s ...", path)
    df = pd.read_csv(
        str(path),
        dtype={"Account Number": str, "Bank ID": str, "Entity ID": str},
    )
    logger.info("[IBM ADAPTER] Loaded %d account rows.", len(df))
    df = normalize_account_columns(df)
    return df


def validate_transaction_schema(df: pd.DataFrame) -> None:
    """
    Validate that the normalized transaction DataFrame has the required columns.
    Raises ValueError with a descriptive message on failure.
    """
    required = {"timestamp", "sender_account", "receiver_account", "amount", "is_laundering"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"[IBM ADAPTER] Normalized transaction DataFrame is missing required columns: {missing}. "
            f"Present columns: {list(df.columns)}"
        )

    # Verify account IDs are not numeric
    for col in ("sender_account", "receiver_account"):
        if pd.to_numeric(df[col], errors="coerce").notna().all():
            logger.warning(
                "[IBM ADAPTER] WARNING: Column '%s' appears to be fully numeric. "
                "Verify that account IDs have not been coerced.", col
            )


def validate_account_schema(df: pd.DataFrame) -> None:
    """
    Validate that the normalized account DataFrame has the required columns.
    """
    required = {"account_id"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"[IBM ADAPTER] Normalized account DataFrame is missing required columns: {missing}."
        )
