# GraphGuard — Graph Intelligence & Fraud Analytics System

GraphGuard is an intelligent transaction-monitoring and graph-based fraud-detection system. Traditional fraud detection systems analyze individual financial transactions in isolation. GraphGuard instead constructs a directed network graph where **Accounts are Nodes** and **Transactions are Edges**, uncovering complex financial crime structures such as **fan-in mule networks**, **fan-out schemes**, **dormancy bursts**, **rapid fund movement**, and **circular money flows**.

---

## 🚀 Key Features

1. **Static Data & Reproducible Generator**: Pre-loaded with synthetic banking datasets (`accounts.csv` and `transactions.csv`) containing realistic normal behaviors alongside injected fraud scenarios.
2. **Deterministic Early Warning Signals (EWS)**: Configurable rules engine monitoring 7 key signals:
   - `EWS-001`: Velocity Spike (high transaction velocity in 1h window)
   - `EWS-002`: Fan-In Mule Account (e.g. 35 unique senders transferring ~₹9,500 within 20 mins)
   - `EWS-003`: Fan-Out Rapid Dispersion (single account spreading funds to 20+ receivers)
   - `EWS-004`: Dormancy Burst (dormant account executing sudden transaction burst)
   - `EWS-005`: Rapid Fund Movement (90%+ of incoming funds transferred out shortly after receipt)
   - `EWS-006`: Suspicious Graph Neighbourhood (high concentration of risky counterparties)
   - `EWS-007`: Circular Money Movement (closed ring flows `A -> B -> C -> D -> A`)
3. **Multi-Signal Risk Fusion Engine**: Combines GNN probabilities (50%), deterministic EWS scores (35%), and graph context metrics (15%) into a unified 0–100 Account Risk Score with human-readable explanations.
4. **Resilient GNN Fallback**: Integrates PyTorch Geometric GraphSAGE node classification with automatic fallback to Random Forest graph features (`ML_ENABLED=false`) to ensure prototype reliability.
5. **Interactive Investigator Dashboard**: Next.js & Tailwind CSS dashboard featuring overview KPIs, account risk distribution, alert triaging, graph topology explorer, and deep-dive account investigation files.

---

## 🏗️ Architecture & Technology Stack

```text
┌──────────────────────────┐
│      Static Dataset       │
│ accounts + transactions   │
└─────────────┬────────────┘
              │
              ▼
┌──────────────────────────┐
│   Python Data Pipeline    │
│ validation + features     │
└─────────────┬────────────┘
              │
              ▼
┌──────────────────────────┐
│      Graph Builder        │
│ NetworkX / PyG graph      │
└─────────────┬────────────┘
              │
       ┌──────┴────────┐
       ▼               ▼
┌─────────────┐ ┌──────────────┐
│ EWS Rules   │ │ ML/GNN Model │
└──────┬──────┘ └───────┬──────┘
       │                │
       └────────┬───────┘
                ▼
       ┌─────────────────┐
       │   Risk Engine   │
       └────────┬────────┘
                ▼
       ┌─────────────────┐
       │ FastAPI Backend │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │ Next.js Frontend│
       │    Dashboard    │
       └─────────────────┘
```

- **Frontend**: Next.js 14, React 18, Tailwind CSS, Lucide Icons, Recharts
- **Backend**: Python 3.14, FastAPI, Pydantic, SQLAlchemy
- **Database**: SQLite (`graphguard.db`)
- **Graph & Machine Learning**: NetworkX, pandas, NumPy, scikit-learn, PyTorch / PyTorch Geometric

---

## ⚡ Quick Start Guide

### Step 1: One-Command Demonstration Setup
Seed the static dataset, build graph topology, extract features, train ML models, run EWS rules, and calculate fused risk scores:

```bash
python scripts/setup_demo.py
```

### Step 2: Launch Backend API
Start the FastAPI backend server:

```bash
cd backend
uvicorn app.main:app --port 8000 --reload
```
- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: `http://localhost:8000/health`

### Step 3: Launch Frontend Dashboard
Open a new terminal window:

```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🎓 Demo Scenario Walkthrough (Professor Presentation Story)

1. **Step 1 — Overview Dashboard**:
   - Open `http://localhost:3000` to inspect total accounts (2,000), transactions (25,000), critical risk accounts, and active alerts.
2. **Step 2 — Search Mule Target `A102`**:
   - Navigate to Accounts or search `A102`.
   - Observe **CRITICAL RISK** (Score: 88 / 100).
3. **Step 3 — Explainable Risk Breakdown**:
   - Note the human-readable reasons:
     - *"35 unique incoming counterparty accounts detected in peak window"* (Fan-In Spike)
     - *"High transaction velocity detected (35 txns/hr)"* (Velocity Spike)
     - *"Transferred out 91% of incoming funds shortly after receipt"* (Rapid Movement)
4. **Step 4 — Graph Explorer**:
   - Open Graph Explorer for `A102` to visually demonstrate the multi-node incoming fan-in structure and rapid outgoing transfers to connected high-risk nodes.

---

## 🧪 Automated Testing

Execute the automated pipeline test suite:

```bash
python tests/test_pipeline.py
```

---

## 📂 Repository Structure

```text
gp/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (accounts, transactions, dashboard, alerts, ews, graph)
│   │   ├── db/           # Database setup (database.py)
│   │   ├── models/       # SQLAlchemy ORM models (models.py)
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # EWS engine, feature extraction, risk fusion logic
│   │   └── main.py       # FastAPI application entry point
├── frontend/
│   ├── src/
│   │   ├── app/          # Next.js App Router (dashboard, accounts, alerts, ews, graph)
│   │   ├── lib/          # API client (api.ts)
├── ml/
│   ├── src/              # Synthetic generator, graph builder, feature extraction, baseline/GNN trainers
│   └── artifacts/        # Scaler, model weights, feature schema, metrics.json
├── data/
│   └── generated/        # accounts.csv & transactions.csv
├── scripts/
│   └── setup_demo.py     # One-command seed & setup script
├── tests/
│   └── test_pipeline.py  # End-to-end unit test suite
└── README.md
```
