"""
GraphGuard FastAPI Main Application
"""

import os
import sys
from pathlib import Path

# Add root project directory to sys.path so 'backend' package is discoverable
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.db.database import engine, Base
from backend.app.api import accounts, transactions, dashboard, alerts, ews, graph

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GraphGuard API",
    description="Intelligent Transaction Monitoring & Graph-based Fraud Detection System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(accounts.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(ews.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "GraphGuard API",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
