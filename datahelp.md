# 📊 GraphGuard Dataset & Data Pipeline Guide

This document provides a comprehensive overview of the dataset powering **GraphGuard**, including data schemas, volume metrics, payment channels, injected money laundering (AML) fraud scenarios, and data generation workflows.

---

## 📈 Dataset Overview

* **Total Monitored Accounts**: `1,065` accounts
* **Total Transactions**: `8,091` transactions
* **Total Financial Volume**: `$64,812,261.29` (~$64.81 Million USD)
* **Date Range**: `2025-11-08T00:00:00` to `2026-02-28T23:59:32` (~4 Months)
* **Storage Format**: Static CSV files in [`data/generated/`](file:///c:/Users/PRASAD%20ARJUN%20RANE/OneDrive/Desktop/gp/data/generated/)

---

## 📂 File Directory Structure

```text
gp/
├── data/
│   ├── generated/
│   │   ├── accounts.csv        # 1,065 Accounts metadata and labels
│   │   └── transactions.csv    # 8,091 Transaction records and labels
│   ├── processed/              # Graph-extracted features and model outputs
│   └── raw/                    # Directory for external raw data ingest
├── ml/
│   └── src/
│       └── generate_data.py    # Synthetic AML dataset generator engine
└── scripts/
    └── setup_demo.py           # End-to-end dataset seeding & model pipeline script
```

---

## 💳 Data Schemas & Field Definitions

### 1. Accounts Schema (`data/generated/accounts.csv`)

| Field Name | Type | Description | Example / Allowed Values |
| :--- | :--- | :--- | :--- |
| `account_id` | String | Unique account identifier | `A0001`, `A102` |
| `account_created_at` | ISO Datetime | Timestamp of account creation | `2025-11-15T10:30:00` |
| `account_type` | Enum String | Type of banking account | `SAVINGS`, `SALARY`, `CURRENT` |
| `status` | Enum String | Account operational state | `ACTIVE` |
| `label` | Integer | Binary classification ground truth | `0` (Legitimate), `1` (Fraud / Mule) |

#### Accounts Distribution
* **Total Accounts**: `1,065`
* **Legitimate Accounts (`label = 0`)**: `1,055` (99.06%)
* **Fraudulent / Mule Accounts (`label = 1`)**: `10` (0.94%)
* **Account Types**:
  * 🏦 `SAVINGS`: `392` accounts (36.8%)
  * 💼 `SALARY`: `341` accounts (32.0%)
  * 🏢 `CURRENT`: `332` accounts (31.2%)

---

### 2. Transactions Schema (`data/generated/transactions.csv`)

| Field Name | Type | Description | Example / Allowed Values |
| :--- | :--- | :--- | :--- |
| `transaction_id` | String | Unique transaction record ID | `TX000001` |
| `sender_account_id` | String | Originating account ID | `A201` |
| `receiver_account_id` | String | Destination account ID | `A102` |
| `amount` | Float | Transaction financial value ($) | `9540.50` |
| `timestamp` | ISO Datetime | Execution timestamp | `2026-02-15T14:05:12` |
| `transaction_type` | Enum String | Payment transfer protocol | `UPI`, `IMPS`, `NEFT`, `TRANSFER` |
| `channel` | Enum String | Digital/Physical banking channel | `MOBILE_APP`, `NET_BANKING`, `ATM` |
| `status` | Enum String | Transfer outcome status | `SUCCESS` |
| `label` | Integer | Binary fraud ground truth | `0` (Normal), `1` (Fraudulent Flow) |

#### Transactions Distribution
* **Total Transactions**: `8,091`
* **Normal Transactions (`label = 0`)**: `8,001`
* **Fraudulent Transactions (`label = 1`)**: `90`

#### Payment Methods Breakdown
* ⚡ **IMPS**: `2,067` transactions (25.5%)
* 📲 **UPI**: `2,033` transactions (25.1%)
* 🔄 **TRANSFER**: `2,012` transactions (24.9%)
* 🏦 **NEFT**: `1,979` transactions (24.5%)

#### Banking Channels Breakdown
* 📱 **MOBILE_APP**: `2,835` transactions (35.0%)
* 💻 **NET_BANKING**: `2,699` transactions (33.4%)
* 🏧 **ATM**: `2,557` transactions (31.6%)

---

## 🚨 Injected Money Laundering (AML) Scenarios

The dataset embeds realistic financial crime mechanics designed to test the 3D Graph Visualizer, NetworkX Centrality Analytics, and Early Warning System (EWS) Rules Engine:

### 1. Fan-In Structuring / Smurfing Hub (`Account A102`)
* **Pattern**: 35 distinct origin accounts send micro-transfers (~$9,200 to $9,800 each) into `A102` within a 20-minute window on Feb 15, 2026.
* **EWS Trigger**: `EWS_HIGH_VELOCITY_STRUCTURING`, `EWS_FAN_IN_SPIKE`.

### 2. Rapid Mule Outflow Layering
* **Pattern**: Immediately following the fan-in concentration, `A102` executes rapid high-value outbound transfers:
  * `$160,000.00` via IMPS to destination account `A301`.
  * `$145,000.00` via IMPS to destination account `A302`.
* **EWS Trigger**: `EWS_RAPID_PASS_THROUGH`, `EWS_HIGH_AMOUNT_BURST`.

### 3. Circular Fund Cycling Ring (`RING-402`)
* **Pattern**: Closed-loop transaction chain between accounts designed to obscure the ultimate beneficial ownership (UBO) and artificially inflate transaction velocity.
* **EWS Trigger**: `EWS_CIRCULAR_FLOW`, `EWS_SUSPICIOUS_NEIGHBOUR_RATIO`.

---

## ⚙️ Data Generation & Pipeline Commands

### Regenerate Synthetic Dataset
To regenerate static dataset files with deterministic seed (`SEED = 42`):
```bash
python -m ml.src.generate_data
```

### Full Setup & Demo Pipeline Seeding
To run full dataset seeding, NetworkX graph building, feature extraction, ML training, EWS rule processing, and risk score fusion:
```bash
python scripts/setup_demo.py
```

### Test Data Pipeline Integrity
To execute automated unit tests verifying dataset loading, schemas, and EWS rules:
```bash
python tests/test_pipeline.py
```
