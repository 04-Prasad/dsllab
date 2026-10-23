"""
GraphGuard One-Command Demonstration Setup Script
Generates static transaction data, builds graph, computes features, runs EWS engine,
trains ML/GNN models, calculates fused risk scores, populates database, and creates alerts.

Usage:
    python scripts/setup_demo.py
"""

import os
import sys
import time
import io

# Force UTF-8 stdout to avoid Windows cp1252 encoding errors
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def banner(text: str):
    width = 68
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def step(n: int, total: int, text: str):
    print(f"\n[Step {n}/{total}] {text}...")


def setup_demo():
    banner("GRAPHGUARD - DEMO SETUP & PIPELINE SEEDING")
    t0 = time.time()

    # ── Step 1: Generate dataset ─────────────────────────────────────────────
    step(1, 9, "Generating synthetic static transactions dataset")
    from ml.src.generate_data import generate_dataset
    accounts_df, transactions_df = generate_dataset(
        num_normal_accounts=1000,
        num_normal_transactions=8000,
        output_dir="data/generated",
    )

    # ── Step 2: Reset database ────────────────────────────────────────────────
    step(2, 9, "Resetting SQLite database schemas")
    from backend.app.db.database import engine, Base, SessionLocal
    from backend.app.models.models import (
        Account, Transaction, AccountFeature, RiskScore, EWSSignal, Alert
    )
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # ── Step 3: Seed accounts and transactions ────────────────────────────────
    step(3, 9, "Importing accounts and transactions into database")
    acc_models = [
        Account(
            account_id=str(r["account_id"]),
            account_created_at=str(r.get("account_created_at", "")),
            account_type=str(r.get("account_type", "SAVINGS")),
            status=str(r.get("status", "ACTIVE")),
            label=int(r.get("label", 0)),
            current_risk_score=0.0,
            current_risk_level="LOW",
        )
        for _, r in accounts_df.iterrows()
    ]
    db.bulk_save_objects(acc_models)
    db.commit()

    tx_models = [
        Transaction(
            transaction_id=str(r["transaction_id"]),
            sender_account_id=str(r["sender_account_id"]),
            receiver_account_id=str(r["receiver_account_id"]),
            amount=float(r["amount"]),
            timestamp=str(r["timestamp"]),
            transaction_type=str(r.get("transaction_type", "TRANSFER")),
            channel=str(r.get("channel", "MOBILE_APP")),
            status=str(r.get("status", "SUCCESS")),
            label=int(r.get("label", 0)),
        )
        for _, r in transactions_df.iterrows()
    ]
    db.bulk_save_objects(tx_models)
    db.commit()
    print(f"   -> Imported {len(acc_models):,} accounts and {len(tx_models):,} transactions.")

    # ── Step 4: Build graph ───────────────────────────────────────────────────
    step(4, 9, "Building NetworkX directed financial transaction graph")
    from ml.src.graph_builder import build_networkx_graph
    G = build_networkx_graph(accounts_df, transactions_df)
    print(f"   -> Graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges.")

    # ── Step 5: Feature extraction ────────────────────────────────────────────
    step(5, 9, "Computing behavioural and network topology features")
    from ml.src.features import extract_features
    features_df = extract_features(accounts_df, transactions_df, G)

    feat_models = [
        AccountFeature(
            account_id=str(r["account_id"]),
            incoming_count=int(r["incoming_transaction_count"]),
            outgoing_count=int(r["outgoing_transaction_count"]),
            incoming_total=float(r["incoming_amount_total"]),
            outgoing_total=float(r["outgoing_amount_total"]),
            unique_senders=int(r["unique_senders"]),
            unique_receivers=int(r["unique_receivers"]),
            velocity_1h=int(r["transaction_velocity_1h"]),
            velocity_24h=int(r["transaction_velocity_24h"]),
            dormancy_days=float(r["dormancy_days"]),
            in_degree=int(r["in_degree"]),
            out_degree=int(r["out_degree"]),
            risky_neighbor_ratio=float(r["risky_neighbor_ratio"]),
        )
        for _, r in features_df.iterrows()
    ]
    db.bulk_save_objects(feat_models)
    db.commit()
    print(f"   -> Features computed for {len(features_df):,} accounts.")

    # ── Step 6: Train ML / GNN models ─────────────────────────────────────────
    step(6, 9, "Training Machine Learning (XGBoost Base, RF) and GNN models")
    from ml.src.train_baseline import train_baseline_model, train_base_model
    from ml.src.train_gnn import train_gnn_model, get_ml_predictions
    try:
        train_base_model(features_df)
    except Exception as e:
        print(f"   ^  XGBoost base model training error (non-fatal): {e}")
    try:
        train_baseline_model(features_df)
    except Exception as e:
        print(f"   ^  Random Forest model training error (non-fatal): {e}")
    try:
        train_gnn_model(features_df, G)
    except Exception as e:
        print(f"   ^  GNN training error (non-fatal): {e}")
    ml_predictions = get_ml_predictions(features_df)
    print(f"   -> ML predictions ready for {len(ml_predictions):,} accounts.")

    # ── Step 7: EWS Engine ───────────────────────────────────────────────────
    step(7, 9, "Running deterministic Early Warning Signal (EWS) rules engine")
    from backend.app.services.ews_service import evaluate_account_ews
    features_dict = features_df.set_index("account_id").to_dict(orient="index")
    ews_total = 0
    ews_records = []

    for acc_id, feat_data in features_dict.items():
        result = evaluate_account_ews(feat_data)
        for sig in result["triggered_signals"]:
            ews_total += 1
            ews_records.append(
                EWSSignal(
                    account_id=str(acc_id),
                    signal_code=sig["code"],
                    signal_type=sig["type"],
                    severity=sig["severity"],
                    description=sig["description"],
                    observed_value=str(sig["observed"]),
                    threshold_value=str(sig["threshold"]),
                    evidence={"account_id": str(acc_id)},
                )
            )

    db.bulk_save_objects(ews_records)
    db.commit()
    print(f"   -> EWS engine triggered {ews_total:,} signals across accounts.")

    # ── Step 8: Risk Fusion ───────────────────────────────────────────────────
    step(8, 9, "Calculating multi-signal risk fusion scores and alert generation")
    from backend.app.services.risk_service import calculate_risk_fusion
    acc_map = {a.account_id: a for a in db.query(Account).all()}

    critical_count = 0
    high_count = 0
    alerts_created = 0
    risk_records = []
    alert_records = []

    for acc_id, feat_data in features_dict.items():
        ews_result = evaluate_account_ews(feat_data)
        ml_prob = ml_predictions.get(str(acc_id), 0.05)
        fusion = calculate_risk_fusion(str(acc_id), ml_prob, ews_result, feat_data, ml_enabled=True)

        # Update account record
        acc_obj = acc_map.get(str(acc_id))
        if acc_obj:
            acc_obj.current_risk_score = fusion["risk_score"]
            acc_obj.current_risk_level = fusion["risk_level"]

        risk_records.append(
            RiskScore(
                account_id=str(acc_id),
                ml_score=fusion["ml_score"],
                ews_score=fusion["ews_score"],
                graph_score=fusion["graph_context_score"],
                final_score=fusion["risk_score"],
                risk_level=fusion["risk_level"],
                reasons=fusion["reasons"],
                model_version="graphsage-v1",
            )
        )

        # Generate alert for HIGH / CRITICAL accounts
        if fusion["risk_level"] in ("HIGH", "CRITICAL"):
            if fusion["risk_level"] == "CRITICAL":
                critical_count += 1
            else:
                high_count += 1

            alerts_created += 1
            primary_reason = (
                fusion["reasons"][0]
                if fusion["reasons"]
                else "Suspicious transaction pattern detected"
            )
            ews_summary = ", ".join(fusion["triggered_ews"]) if fusion["triggered_ews"] else "N/A"

            alert_records.append(
                Alert(
                    alert_id=f"ALT-{alerts_created:04d}",
                    account_id=str(acc_id),
                    severity=fusion["risk_level"],
                    risk_score=fusion["risk_score"],
                    title=f"{fusion['risk_level']} Risk Detected - {acc_id}",
                    description=f"{primary_reason}. EWS: {ews_summary}",
                    status="NEW",
                )
            )

    db.bulk_save_objects(risk_records)
    db.bulk_save_objects(alert_records)
    db.commit()

    # ── Step 9: Verify seeded data ────────────────────────────────────────────
    step(9, 9, "Verifying seeded data integrity")
    from sqlalchemy import func
    total_accs = db.query(func.count(Account.id)).scalar()
    total_txs = db.query(func.count(Transaction.id)).scalar()
    total_alerts = db.query(func.count(Alert.id)).scalar()
    total_ews = db.query(func.count(EWSSignal.id)).scalar()
    db.close()

    elapsed = time.time() - t0
    banner("GRAPHGUARD DEMO SETUP COMPLETED SUCCESSFULLY")
    print(f"  Total Accounts Monitored  : {total_accs:,}")
    print(f"  Total Transactions        : {total_txs:,}")
    print(f"  Total Graph Nodes         : {G.number_of_nodes():,}")
    print(f"  Total Graph Edges         : {G.number_of_edges():,}")
    print(f"  Total EWS Triggered       : {total_ews:,}")
    print(f"  Critical Risk Accounts    : {critical_count:,}")
    print(f"  High Risk Accounts        : {high_count:,}")
    print(f"  Investigator Alerts       : {total_alerts:,}")
    print(f"  Setup Time                : {elapsed:.1f}s")
    print("=" * 68)
    print()
    print("  Demo target A102 (Fan-In Mule) is seeded and ready.")
    print()
    print("  > Start Backend : cd backend && uvicorn app.main:app --port 8000 --reload")
    print("  > Open Dashboard: http://localhost:3000")
    print()


if __name__ == "__main__":
    import argparse
    from config.settings import settings

    parser = argparse.ArgumentParser(description="GraphGuard Setup Script")
    parser.add_argument(
        "--source",
        choices=["ibm", "synthetic"],
        default=settings.DATA_SOURCE,
        help="Data source to seed: 'ibm' (default) or 'synthetic'",
    )
    parser.add_argument("--sample-rows", type=int, default=50000, help="Number of IBM transactions to sample")
    args = parser.parse_args()

    if args.source == "ibm":
        from scripts.setup_ibm import setup_ibm_pipeline
        setup_ibm_pipeline(sample_rows=args.sample_rows)
    else:
        setup_demo()
