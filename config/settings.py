"""
GraphGuard Centralised Configuration
Reads all settings from environment variables / .env files.

Usage:
    from config.settings import settings
    settings.IBM_DATA_DIR
    settings.DATA_SOURCE
"""

import os
from pathlib import Path

# Try loading .env file from project root
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent
    _env_file = _root / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
    # Also try backend/.env
    _backend_env = _root / "backend" / ".env"
    if _backend_env.exists():
        load_dotenv(_backend_env, override=False)
except ImportError:
    pass  # python-dotenv not installed -- env vars must be set externally


class Settings:
    """
    GraphGuard runtime configuration loaded from environment variables.

    Key variables:
        DATA_SOURCE     : "ibm" (default) or "synthetic"
        IBM_DATA_DIR    : Path to directory containing IBM AML CSV files.
                          Default: ./data/raw/ibm
        DATABASE_URL    : SQLAlchemy database URL. Default: SQLite at project root.
        ML_ENABLED      : "true"/"false" -- whether ML models are active.
    """

    # Project root
    ROOT_DIR: Path = Path(__file__).resolve().parent.parent

    # ── Data source selection ─────────────────────────────────────────────────
    # "ibm"       -> use IBM AML dataset (LI-Small_Trans.csv / LI-Small_accounts.csv)
    # "synthetic" -> use generated synthetic dataset (data/generated/)
    DATA_SOURCE: str = os.getenv("DATA_SOURCE", "ibm").lower()

    # ── IBM dataset configuration ─────────────────────────────────────────────
    # IBM_DATA_DIR is configurable for:
    #   - Local development:  IBM_DATA_DIR=./data/raw/ibm
    #   - Google Colab:       IBM_DATA_DIR=/content/drive/MyDrive/GraphGuard_Data
    #   - Server deployment:  IBM_DATA_DIR=/server/data/ibm
    _default_ibm_dir = (
        Path(__file__).resolve().parent.parent / "data"
        if (Path(__file__).resolve().parent.parent / "data" / "LI-Small_Trans.csv").exists()
        else Path(__file__).resolve().parent.parent / "data" / "raw" / "ibm"
    )
    _ibm_data_dir_raw: str = os.getenv("IBM_DATA_DIR", str(_default_ibm_dir))
    IBM_DATA_DIR: Path = Path(_ibm_data_dir_raw)

    IBM_TRANSACTIONS_FILE: str = os.getenv("IBM_TRANSACTIONS_FILE", "LI-Small_Trans.csv")
    IBM_ACCOUNTS_FILE: str = os.getenv("IBM_ACCOUNTS_FILE", "LI-Small_accounts.csv")

    # ── Synthetic dataset configuration ───────────────────────────────────────
    SYNTHETIC_DATA_DIR: Path = ROOT_DIR / "data" / "generated"
    SYNTHETIC_ACCOUNTS_FILE: str = "accounts.csv"
    SYNTHETIC_TRANSACTIONS_FILE: str = "transactions.csv"

    # ── Processed data / cache ────────────────────────────────────────────────
    PROCESSED_DATA_DIR: Path = ROOT_DIR / "data" / "processed"

    # ── ML artifacts ──────────────────────────────────────────────────────────
    ML_ARTIFACTS_DIR: Path = ROOT_DIR / "ml" / "artifacts"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{ROOT_DIR / 'graphguard.db'}"
    )

    # ── ML runtime ────────────────────────────────────────────────────────────
    ML_ENABLED: bool = os.getenv("ML_ENABLED", "true").lower() == "true"

    # ── IBM preprocessing options ─────────────────────────────────────────────
    # Number of rows to sample from IBM dataset (0 = all rows)
    IBM_SAMPLE_ROWS: int = int(os.getenv("IBM_SAMPLE_ROWS", "0"))

    # Whether to use cached Parquet files if they exist
    USE_PARQUET_CACHE: bool = os.getenv("USE_PARQUET_CACHE", "true").lower() == "true"

    # Maximum transactions to insert into SQLite (0 = no raw transactions in DB)
    # For IBM dataset with 1M+ rows, we do NOT bulk insert raw transactions.
    # Only account-level features and risk scores go to the database.
    MAX_TRANSACTIONS_IN_DB: int = int(os.getenv("MAX_TRANSACTIONS_IN_DB", "0"))

    @property
    def ibm_transactions_path(self) -> Path:
        return self.IBM_DATA_DIR / self.IBM_TRANSACTIONS_FILE

    @property
    def ibm_accounts_path(self) -> Path:
        return self.IBM_DATA_DIR / self.IBM_ACCOUNTS_FILE

    @property
    def synthetic_accounts_path(self) -> Path:
        return self.SYNTHETIC_DATA_DIR / self.SYNTHETIC_ACCOUNTS_FILE

    @property
    def synthetic_transactions_path(self) -> Path:
        return self.SYNTHETIC_DATA_DIR / self.SYNTHETIC_TRANSACTIONS_FILE

    @property
    def processed_transactions_parquet(self) -> Path:
        return self.PROCESSED_DATA_DIR / "transactions.parquet"

    @property
    def processed_account_features_parquet(self) -> Path:
        return self.PROCESSED_DATA_DIR / "account_features.parquet"

    @property
    def processed_accounts_parquet(self) -> Path:
        return self.PROCESSED_DATA_DIR / "accounts.parquet"

    def validate_ibm_files(self) -> None:
        """Raise FileNotFoundError with helpful message if IBM files are missing."""
        if not self.ibm_transactions_path.exists():
            raise FileNotFoundError(
                f"[IBM DATA] IBM transaction dataset not found.\n"
                f"Expected: {self.ibm_transactions_path}\n"
                f"Configure IBM_DATA_DIR environment variable and ensure "
                f"'{self.IBM_TRANSACTIONS_FILE}' exists in that directory.\n"
                f"Example: IBM_DATA_DIR=/content/drive/MyDrive/GraphGuard_Data"
            )
        if not self.ibm_accounts_path.exists():
            raise FileNotFoundError(
                f"[IBM DATA] IBM accounts file not found.\n"
                f"Expected: {self.ibm_accounts_path}\n"
                f"Configure IBM_DATA_DIR environment variable and ensure "
                f"'{self.IBM_ACCOUNTS_FILE}' exists in that directory."
            )

    def describe_ibm_source(self) -> str:
        """A safe, explicit description suitable for pipeline logs."""
        return f"{self.ibm_transactions_path.name} ({self.ibm_transactions_path})"

    def __repr__(self) -> str:
        return (
            f"Settings("
            f"DATA_SOURCE={self.DATA_SOURCE!r}, "
            f"IBM_DATA_DIR={self.IBM_DATA_DIR}, "
            f"ML_ENABLED={self.ML_ENABLED}"
            f")"
        )


# Singleton instance
settings = Settings()
