"""
GraphGuard SQLite Database Configuration
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from pathlib import Path

# Always resolve graphguard.db relative to the project root directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_DB = f"sqlite:///{ROOT_DIR / 'graphguard.db'}"
DB_PATH = os.getenv("DATABASE_URL", DEFAULT_DB)

engine = create_engine(
    DB_PATH,
    connect_args={"check_same_thread": False} if DB_PATH.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
