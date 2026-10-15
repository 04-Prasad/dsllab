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

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.app.db.database import engine, Base
from backend.app.api import accounts, transactions, dashboard, alerts, ews, graph, models, auth, users
from backend.app.api.deps import RoleChecker

all_roles = RoleChecker(["ADMIN", "INVESTIGATOR", "ANALYST"])

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

def seed_default_users():
    from backend.app.db.database import SessionLocal
    from backend.app.models.models import User
    from backend.app.core.security import get_password_hash
    db = SessionLocal()
    try:
        defaults = [
            ("admin@graphguard.ai", "admin1234", "Admin User", "ADMIN"),
            ("investigator@graphguard.ai", "investigator123", "Lead Investigator", "INVESTIGATOR"),
            ("analyst@graphguard.ai", "analyst123", "AML Analyst", "ANALYST"),
        ]
        for email, pwd, name, role in defaults:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(
                    email=email,
                    password_hash=get_password_hash(pwd),
                    full_name=name,
                    role=role,
                    is_active=1,
                ))
        db.commit()
    finally:
        db.close()

seed_default_users()

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
app.include_router(dashboard.router, prefix="/api/v1", dependencies=[Depends(all_roles)])
app.include_router(accounts.router, prefix="/api/v1", dependencies=[Depends(all_roles)])
app.include_router(transactions.router, prefix="/api/v1", dependencies=[Depends(all_roles)])
app.include_router(alerts.router, prefix="/api/v1") # Alerts has its own internal granular RoleCheckers
app.include_router(ews.router, prefix="/api/v1", dependencies=[Depends(all_roles)])
app.include_router(graph.router, prefix="/api/v1", dependencies=[Depends(all_roles)])
app.include_router(models.router, prefix="/api/v1", dependencies=[Depends(all_roles)])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(auth.router, prefix="/api/v1/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

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
