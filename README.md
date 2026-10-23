# GraphGuard — Graph Intelligence & AML Financial Crime Detection

GraphGuard is an intelligent transaction monitoring and graph-based anti-money laundering (AML) detection platform. Designed for final-year engineering research and production-grade monitoring, GraphGuard moves beyond isolated single-transaction rules by representing financial transactions as a directed graph where **Accounts are Nodes** and **Transactions are Edges**.

By fusing **tabular machine learning (Random Forest, AdaBoost)**, **Graph Neural Networks (GraphSAGE)**, **NetworkX topological analytics (PageRank, cycle detection)**, and **deterministic Early Warning Signals (EWS)**, GraphGuard identifies high-risk laundering patterns such as **fan-in smurfing**, **rapid mule layering**, **dormancy bursts**, and **closed circular cycling rings**.

> **Academic & Compliance Notice:**
> *The IBM Transactions for Anti-Money Laundering (AML) dataset is used as the primary experimental dataset. The generated AML Risk Score represents a model-derived statistical indicator and does not constitute conclusive legal proof of financial crime.*

---

## 🏛️ System Architecture

```text
                             IBM AML DATASET
                 (LI-Small_Trans.csv / LI-Small_accounts.csv)
                                   │
                                   ▼
                            IBM DATA ADAPTER
               (Schema Normalization & String ID Enforcement)
                                   │
                                   ▼
                        DATA PREPROCESSING ENGINE
            (Cleaning, Validation, Temporal Parsing & Parquet Cache)
                                   │
                                   ▼
                      FEATURE ENGINEERING ENGINE
           (22 Behavioral, Temporal & Graph Centrality Features)
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
   RANDOM FOREST                ADABOOST                 GRAPHSAGE
(Tabular Baseline)        (Boosting Comparison)      (Graph Neural Net)
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼
                       MODEL COMPARISON & METRICS
               (Precision, Recall, F1-Score, ROC-AUC, CM)
                                   │
                                   ▼
                        DYNAMIC MODEL SELECTION
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
 DETERMINISTIC EWS ENGINE                             RISK FUSION ENGINE
 (7 Rule-based Signals)                             (ML + EWS + Graph → 0-100)
         │                                                   │
         └─────────────────────────┬─────────────────────────┘
                                   ▼
                        FASTAPI BACKEND & SQLITE
                                   │
                                   ▼
                       NEXT.JS / REACT FRONTEND
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
   KPI Overview             3D Network Graph          Account Deep-Dive
```

---

## 📊 Dataset & Pipeline Configuration

### 1. IBM Transactions for AML Dataset
GraphGuard uses the IBM AML dataset (`LI-Small_Trans.csv` and `LI-Small_accounts.csv`):
- **LI-Small_Trans.csv**: 6,924,049 transaction records with timestamps, sender/receiver bank IDs, duplicate `Account` columns, monetary amounts in multiple currencies, payment formats, and binary `Is Laundering` labels.
- **LI-Small_accounts.csv**: 712,688 account records containing bank names, bank IDs, account numbers, and entity mappings.

### 2. Environment Variables & Path Configuration
The dataset location is fully configurable across local development, Google Colab, and production servers via environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATA_SOURCE` | `ibm` | Primary data source (`ibm` or `synthetic`) |
| `IBM_DATA_DIR` | `./data` | Directory containing `LI-Small_Trans.csv` & `LI-Small_accounts.csv` |
| `USE_PARQUET_CACHE` | `true` | Caches normalized DataFrames to `data/processed/*.parquet` |
| `DATABASE_URL` | `sqlite:///./graphguard.db` | SQLAlchemy database connection URI |
| `ML_ENABLED` | `true` | Enables/disables machine learning scoring |

#### Google Colab / Cloud Storage Configuration
To run on Google Colab with data mounted in Google Drive:
```bash
export IBM_DATA_DIR="/content/drive/MyDrive/GraphGuard_Data"
export DATA_SOURCE="ibm"
```

---

## 🔬 Machine Learning & Graph Neural Networks

### 1. Evaluated Models & Base Model
GraphGuard implements and benchmarks four distinct models, designating **XGBoost** as the production base model:

1. **XGBoost Classifier (Designated Base Model)**:
   - Gradient boosted decision trees optimized with `scale_pos_weight` to address AML class imbalance (~0.05% positive prevalence).
   - Features precision-recall threshold tuning on validation splits to minimize alert fatigue while maintaining >= 90% recall.
   - Deployed as the primary production base model for fused risk scoring and alert generation.
2. **Random Forest Classifier**:
   - Ensemble of 100 decision trees with balanced class weights and max depth = 8.
   - Provides a traditional tabular baseline and calculates Gini feature importances.
3. **AdaBoost Classifier**:
   - Adaptive boosting ensemble with decision stump base learners and class-weighted rebalancing.
   - Serves as the boosting-based comparative baseline.
4. **GraphSAGE (Graph Neural Network)**:
   - 2-layer mean-aggregation convolutional network ($h_{\mathcal{N}(v)}$) implemented in PyTorch.
   - Captures relational structure across transaction counterparties and neighborhood topologies.

### 2. Metric Evaluation Strategy
Because AML transaction datasets exhibit extreme class imbalance (~0.05% laundering transactions), **Accuracy is never used as the primary metric**. The system evaluates models using:
- **Recall**: Measures the fraction of actual money laundering accounts successfully caught.
- **Precision**: Measures the fraction of flagged accounts that are truly suspicious.
- **F1-Score**: Harmonic mean of Precision and Recall.
- **ROC-AUC**: Receiver Operating Characteristic Area Under the Curve.
- **Confusion Matrix**: True Positives, False Positives, True Negatives, False Negatives.

The system dynamically designates the **Best Model** based on experimental F1-Score and Recall.

### 3. Feature Engineering & Strict Leakage Prevention
Account features are derived from transaction aggregates and graph properties without leaking the ground-truth target:
- **Volume & Value**: Total transactions, incoming/outgoing counts, total amounts, average amounts, max transaction amount.
- **Counterparties**: Unique senders, unique receivers, fan-in ratio, fan-out ratio.
- **Temporal & Velocity**: 1-hour transaction velocity, 24-hour transaction velocity, dormancy gap days, account age.
- **Graph Topology**: In-degree, out-degree, total degree, PageRank centrality, bounded cycle indicator (circular flow).
- **Leakage Prevention**: Neither `Is Laundering` nor direct laundering-derived counts are included in feature matrices.

---

## 🚨 Deterministic Early Warning Signals (EWS)

GraphGuard executes 7 deterministic AML rules:
- `EWS-001` (**VELOCITY_SPIKE**): More than 15 transactions within a 1-hour rolling window.
- `EWS-002` (**FAN_IN_SPIKE**): More than 10 unique senders transferring funds into a single account (smurfing/structuring).
- `EWS-003` (**FAN_OUT_SPIKE**): More than 10 unique receivers receiving funds from a single account.
- `EWS-004` (**DORMANCY_BURST**): Account dormant for >30 days suddenly executes burst activity.
- `EWS-005` (**RAPID_MOVEMENT**): Account transfers out >80% of received funds (pass-through mule).
- `EWS-006` (**SUSPICIOUS_NEIGHBOUR**): High concentration of flagged counterparties in graph neighborhood.
- `EWS-007` (**CIRCULAR_FLOW**): Account is part of a closed transaction cycle (lengths 2–4).

---

## 🎯 Multi-Signal Risk Score Fusion (0–100)

The final Account AML Risk Score is computed through calibrated fusion:
$$\text{Risk Score} = 0.50 \times \text{ML Score} + 0.35 \times \text{EWS Score} + 0.15 \times \text{Graph Context Score}$$

Risk Level categorization:
- **LOW** (`0 – 29`): Normal banking patterns.
- **MEDIUM** (`30 – 59`): Minor behavioral anomalies.
- **HIGH** (`60 – 79`): Multiple risk triggers or high ML anomaly probability.
- **CRITICAL** (`80 – 100`): Urgent AML investigation required (automated alert generated).

---

## 🚀 Execution Guide

### 1. Setup & Train IBM Pipeline
Run the end-to-end pipeline (preprocess IBM data, build graph, extract features, train all models, generate risk scores, seed database):

```bash
# Default (50,000 transaction sample for fast execution)
python scripts/setup_ibm.py

# Custom sample size
python scripts/setup_ibm.py --sample-rows 100000

# Force recompute without using Parquet cache
python scripts/setup_ibm.py --force-recompute
```

### 2. Run Synthetic Fallback Mode (Optional)
To verify synthetic mode compatibility:
```bash
python scripts/setup_demo.py --source synthetic
```

### 3. Start Backend API
```bash
cd backend
uvicorn app.main:app --port 8000 --reload
```
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Model Metrics API: [http://localhost:8000/api/v1/models/metrics](http://localhost:8000/api/v1/models/metrics)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 4. Start Frontend UI
```bash
cd frontend
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 5. Run Automated Tests
```bash
python -m unittest tests/test_ibm_pipeline.py
```

---

## 📁 Repository Structure

```text
gp/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routes (accounts, dashboard, graph, models, etc.)
│   │   ├── db/              # SQLAlchemy database engine and session
│   │   ├── models/          # ORM data models (Account, Transaction, RiskScore, etc.)
│   │   ├── schemas/         # Pydantic validation schemas
│   │   └── services/        # Business logic (ews_service, risk_service, graph_service)
│   ├── .env                 # Backend environment settings
│   └── main.py              # Application entrypoint
├── config/
│   └── settings.py          # Centralized configuration with env-variable fallbacks
├── data/
│   ├── LI-Small_Trans.csv   # IBM AML Transactions dataset (raw reference)
│   ├── LI-Small_accounts.csv# IBM AML Accounts metadata dataset (raw reference)
│   ├── generated/           # Synthetic fallback data
│   └── processed/           # Cached Parquet features & normalized tables
├── frontend/                # Next.js 14, React, Tailwind CSS 3D visualization dashboard
├── ml/
│   ├── artifacts/           # Trained models (.pkl, .pt) and metrics.json
│   └── src/
│       ├── ibm_adapter.py   # IBM raw column normalization & string ID enforcer
│       ├── ibm_preprocessing.py # Chunked loading, cleaning, & Parquet caching
│       ├── features.py      # 22-feature account extraction engine
│       ├── graph_builder.py # NetworkX directed graph builder
│       ├── train_baseline.py# Random Forest trainer & multi-model comparison
│       ├── train_adaboost.py# AdaBoost classifier trainer
│       └── train_gnn.py     # Native PyTorch GraphSAGE trainer & inference
├── scripts/
│   ├── setup_ibm.py         # End-to-end IBM pipeline seeding & training script
│   └── setup_demo.py        # Demo script supporting both IBM and synthetic sources
└── tests/
    └── test_ibm_pipeline.py # Comprehensive unit & integration test suite
```
