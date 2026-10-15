"""
GraphGuard IBM AML Pipeline Setup Script
========================================
End-to-end pipeline execution for the IBM Transactions for AML dataset:
1. Data Ingestion & Schema Normalization via IBM Adapter
2. Preprocessing & Parquet Caching
3. Directed Graph Construction (NetworkX)
4. Account Feature Engineering (22 Behavioral & Graph Features)
5. Multi-Model Training & Evaluation (Random Forest vs AdaBoost vs GraphSAGE)
6. Dynamic Best Model Selection & Metrics Persistence
7. Deterministic Early Warning System (EWS) Rules Engine
8. Risk Score Fusion (0-100) & Automated Alert Generation
9. Database Population (SQLite)

Usage:
    python scripts/setup_ibm.py
    python scripts/setup_ibm.py --sample-rows 50000
    python scripts/setup_ibm.py --force-recompute
"""

import os
import sys
import time
import io
import argparse
from pathlib import Path

# Force UTF-8 stdout
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except AttributeError:
    pass

# Ensure project root is on sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from config.settings import settings


def banner(text: str):
    width = 72
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def step(n: int, total: int, text: str):
    print(f"\n[Step {n}/{total}] {text}...")


def setup_ibm_pipeline(
    sample_rows: int = 50000,
    force_recompute: bool = False,
    max_db_txs: int = 25000,
    reset_db: bool = False,
    allow_insufficient_labels: bool = False,
    min_positives: int = 8,
):
    banner("GRAPHGUARD — IBM AML PIPELINE INITIALIZATION & MODEL TRAINING")
    t0 = time.time()

    # Check persistence before expensive source loading. A reset remains an
    # explicit action and never drops user or audit tables.
    from backend.app.db.database import engine, Base, SessionLocal
    from backend.app.models.models import Account, Transaction, AccountFeature, RiskScore, EWSSignal, Alert
    Base.metadata.create_all(bind=engine)
    preflight_db = SessionLocal()
    existing_accounts = preflight_db.query(Account).count()
    preflight_db.close()
    if existing_accounts and not reset_db:
        raise RuntimeError(
            "Pipeline tables already contain data. Re-run with --reset-db to replace "
            "only generated pipeline records; user and audit tables are preserved."
        )

    # ── Step 1: Preprocess IBM Dataset ───────────────────────────────────────
    step(1, 9, f"Loading & preprocessing IBM AML dataset (requested rows={sample_rows or 'all'})")
    from ml.src.ibm_preprocessing import run_ibm_preprocessing

    tx_df, acc_df, prep_stats = run_ibm_preprocessing(
        sample_rows=sample_rows,
        force_recompute=force_recompute,
    )
    pos_txs = prep_stats.get("laundering_transactions", int((tx_df["is_laundering"] == 1).sum()))
    total_txs = len(tx_df)
    pos_accs = prep_stats.get("suspicious_accounts", int((acc_df["label"] == 1).sum()))
    total_accs = len(acc_df)
    tx_pos_pct = prep_stats.get("laundering_ratio_pct", round(pos_txs / max(1, total_txs) * 100, 4))
    acc_pos_pct = prep_stats.get("suspicious_account_ratio_pct", round(pos_accs / max(1, total_accs) * 100, 4))

    print("\n   [DATASET DIAGNOSTICS]")
    print(f"   -> Source File           : {settings.describe_ibm_source()}")
    print(f"   -> Cache Status          : {prep_stats.get('cache_status', 'unknown')}")
    print(f"   -> Ingestion Window      : {f'First {sample_rows:,} rows' if sample_rows > 0 else 'Full dataset'}")
    print(f"   -> Transactions Loaded   : {total_txs:,} (Cleaned: {total_txs:,}, Laundering: {pos_txs:,} [{tx_pos_pct:.4f}%], Normal: {total_txs - pos_txs:,})")
    print(f"   -> Accounts Derived      : {total_accs:,} (Suspicious: {pos_accs:,} [{acc_pos_pct:.4f}%], Legitimate: {total_accs - pos_accs:,})")
    print(f"   -> Database Tx Cap       : {max_db_txs:,} (Index limit in SQLite; full transactions used for graph & features)")
    print(f"   -> Full Dataset Baseline : 6,924,049 rows total in LI-Small_Trans.csv with 3,565 laundering transactions (0.0515%)")

    # ── Step 2: Reset Database ────────────────────────────────────────────────
    step(2, 9, "Preparing SQLite pipeline tables")
    from backend.app.models.models import (
        Account, Transaction, AccountFeature, RiskScore, EWSSignal, Alert
    )
    db = SessionLocal()
    if reset_db:
        # Do not drop the complete schema: authentication and audit data are user work.
        for model in (Alert, EWSSignal, RiskScore, AccountFeature, Transaction, Account):
            db.query(model).delete()
        db.commit()

    # ── Step 3: Seed Accounts & Representative Transactions ───────────────────
    step(3, 9, "Seeding account records & representative transactions into database")
    acc_models = [
        Account(
            account_id=str(r["account_id"]),
            account_created_at=str(r.get("account_created_at", "")),
            account_type=str(r.get("account_type", "CURRENT")),
            status=str(r.get("status", "ACTIVE")),
            label=int(r.get("label", 0)),
            current_risk_score=0.0,
            current_risk_level="LOW",
        )
        for _, r in acc_df.iterrows()
    ]
    db.bulk_save_objects(acc_models)
    db.commit()

    # Insert representative transactions (capped to keep SQLite performant)
    db_tx_slice = tx_df.head(max_db_txs) if max_db_txs > 0 else tx_df
    tx_models = [
        Transaction(
            transaction_id=str(r["transaction_id"]),
            sender_account_id=str(r["sender_account_id"]),
            receiver_account_id=str(r["receiver_account_id"]),
            amount=float(r["amount"]),
            timestamp=str(r["timestamp"]),
            transaction_type=str(r.get("payment_format", "TRANSFER")),
            channel="ELECTRONIC",
            status="SUCCESS",
            label=int(r.get("is_laundering", 0)),
        )
        for _, r in db_tx_slice.iterrows()
    ]
    db.bulk_save_objects(tx_models)
    db.commit()
    print(f"   -> Seeded {len(acc_models):,} accounts and {len(tx_models):,} transactions in SQLite.")

    # ── Step 4: Build NetworkX Graph ──────────────────────────────────────────
    step(4, 9, "Constructing NetworkX directed transaction graph")
    from ml.src.graph_builder import build_networkx_graph
    G = build_networkx_graph(acc_df, tx_df)
    print(f"   -> Transaction Graph: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges.")

    # ── Step 5: Feature Engineering ───────────────────────────────────────────
    step(5, 9, "Extracting behavioral, temporal, and topological features")
    from ml.src.features import extract_features
    features_df = extract_features(acc_df, tx_df, G)

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
    print(f"   -> Features computed and saved for {len(features_df):,} accounts.")

    # ── Step 6: Multi-Model Training & Evaluation ─────────────────────────────
    step(6, 9, "Training & comparing ML models (Random Forest, AdaBoost, GraphSAGE)")
    from ml.src.train_baseline import train_all_models, InsufficientLabelsError
    from ml.src.train_gnn import get_ml_predictions

    model_metrics = {}
    ml_predictions = {}
    training_skipped = False

    print(f"   -> Account Ground Truth  : positive={pos_accs:,} ({acc_pos_pct:.4f}%), negative={total_accs - pos_accs:,}")
    print(f"   -> Stratified Split Req  : minimum {min_positives} positive accounts required for reliable evaluation holdout")

    try:
        model_metrics = train_all_models(
            features_df,
            G,
            allow_insufficient_labels=allow_insufficient_labels,
            min_required=min_positives,
        )
        if model_metrics.get("status") == "SKIPPED_INSUFFICIENT_LABELS":
            training_skipped = True
            print(f"   -> [NOTICE] ML evaluation skipped: {model_metrics['diagnostics']['reason']}")
            print(f"   -> [RECOMMENDATION] {model_metrics['diagnostics']['recommendation']}")
        else:
            ml_predictions = get_ml_predictions(features_df, G)
            print(f"   -> Model comparison complete. Best Model: {model_metrics.get('best_model_display')}")
    except InsufficientLabelsError as e:
        print(f"\n   [ERROR] INSUFFICIENT POSITIVE LABELS FOR RELIABLE EVALUATION:")
        print(f"   -> Identified only {e.pos_count} positive accounts (need at least {e.min_required} for stratified train/test split).")
        print(f"   -> In the chronologically sorted IBM dataset, money laundering begins gradually.")
        print(f"   -> A sample of {sample_rows:,} transactions captured only {pos_txs} laundering events.")
        print(f"\n   OPTIONS TO PROCEED:")
        print(f"   1. Train genuine models: re-run with --sample-rows 200000 or higher (or omit --sample-rows) to ingest >= 8 positive accounts.")
        print(f"   2. Complete data preparation: re-run with --allow-insufficient-labels to finish database seeding, graph construction, and deterministic EWS scoring.")
        raise

    # ── Step 7: Deterministic EWS Rules Engine ───────────────────────────────
    step(7, 9, "Evaluating deterministic Early Warning Signals (EWS)")
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

    # ── Step 8: Multi-Signal Risk Fusion & Alert Generation ───────────────────
    step(8, 9, "Computing multi-signal fused risk scores (0-100) & generating alerts")
    from backend.app.services.risk_service import calculate_risk_fusion

    ml_active = (not training_skipped) and bool(ml_predictions)
    if ml_active:
        print(f"   -> Risk Fusion Policy    : Active ML ({model_metrics.get('best_model_display')}) [50%] + EWS [35%] + Graph Topology [15%]")
    else:
        print("   -> Risk Fusion Policy    : Fallback mode (ML not evaluated) -> EWS [70%] + Graph Topology [30%]")

    acc_map = {a.account_id: a for a in db.query(Account).all()}
    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0
    alerts_created = 0
    risk_records = []
    alert_records = []

    for acc_id, feat_data in features_dict.items():
        ews_result = evaluate_account_ews(feat_data)
        ml_prob = ml_predictions.get(str(acc_id)) if ml_active else 0.0
        fusion = calculate_risk_fusion(str(acc_id), ml_prob, ews_result, feat_data, ml_enabled=ml_active)

        acc_obj = acc_map.get(str(acc_id))
        if acc_obj:
            acc_obj.current_risk_score = fusion["risk_score"]
            acc_obj.current_risk_level = fusion["risk_level"]

        risk_lvl = fusion["risk_level"]
        if risk_lvl == "CRITICAL":
            critical_count += 1
        elif risk_lvl == "HIGH":
            high_count += 1
        elif risk_lvl == "MEDIUM":
            medium_count += 1
        else:
            low_count += 1

        risk_records.append(
            RiskScore(
                account_id=str(acc_id),
                ml_score=fusion["ml_score"] if ml_active else 0.0,
                ews_score=fusion["ews_score"],
                graph_score=fusion["graph_context_score"],
                final_score=fusion["risk_score"],
                risk_level=fusion["risk_level"],
                reasons=fusion["reasons"],
                model_version=f"{model_metrics.get('best_model', 'rf')}-v1" if ml_active else "none-ews-fallback",
            )
        )

        if risk_lvl in ("HIGH", "CRITICAL"):
            alerts_created += 1
            primary_reason = fusion["reasons"][0] if fusion["reasons"] else "AML Risk Pattern Detected"
            ews_summary = ", ".join(fusion["triggered_ews"]) if fusion["triggered_ews"] else "N/A"
            alert_records.append(
                Alert(
                    alert_id=f"ALT-{alerts_created:04d}",
                    account_id=str(acc_id),
                    severity=risk_lvl,
                    risk_score=fusion["risk_score"],
                    title=f"{risk_lvl} AML Risk Detected - {acc_id}",
                    description=f"{primary_reason}. EWS Signals: {ews_summary}",
                    status="NEW",
                )
            )

    db.bulk_save_objects(risk_records)
    db.bulk_save_objects(alert_records)
    db.commit()
    print(f"   -> Fused risk scores generated for {len(risk_records):,} accounts.")
    print(f"   -> Generated {alerts_created:,} investigator alerts (Critical: {critical_count}, High: {high_count}).")

    # ── Step 9: Pipeline Summary ──────────────────────────────────────────────
    step(9, 9, "Verifying seeded dataset & printing evaluation report")
    from sqlalchemy import func
    total_db_accs = db.query(func.count(Account.id)).scalar()
    total_db_txs = db.query(func.count(Transaction.id)).scalar()
    top_risky = db.query(Account).order_by(Account.current_risk_score.desc()).limit(5).all()
    db.close()

    elapsed = time.time() - t0
    if training_skipped:
        banner("GRAPHGUARD — IBM AML PIPELINE COMPLETED (DATA PREPARATION & EWS)")
    else:
        banner("GRAPHGUARD — IBM AML PIPELINE COMPLETED SUCCESSFULLY")

    print(f"  Execution Time               : {elapsed:.1f} seconds")
    print(f"  Total Monitored Accounts     : {total_db_accs:,}")
    print(f"  Total Indexed Transactions   : {total_db_txs:,}")
    print(f"  Graph Topology               : {G.number_of_nodes():,} nodes, {G.number_of_edges():,} directed edges")
    print(f"  Risk Distribution            : CRITICAL: {critical_count} | HIGH: {high_count} | MEDIUM: {medium_count} | LOW: {low_count}")
    print(f"  Generated Alerts             : {alerts_created:,}")
    if training_skipped:
        print(f"  ML Model Evaluation          : SKIPPED (insufficient positive labels: {pos_accs} found, {min_positives} required)")
        print(f"  Risk Scoring Method          : Deterministic EWS Rules (70%) + Graph Topology (30%)")
    else:
        print(f"  Best ML Model Selected       : {model_metrics.get('best_model_display')}")
        print("\n  MODEL COMPARISON MATRIX:")
        print("  " + "-" * 76)
        print(f"  {'Model':<22} | {'Precision':<9} | {'Recall':<8} | {'F1-Score':<8} | {'ROC-AUC':<8} | {'PR-AUC':<8}")
        print("  " + "-" * 76)
        for m_key, m_val in model_metrics.get("models_comparison", {}).items():
            print(f"  {m_val['model_name']:<22} | {m_val['precision']:<9.4f} | {m_val['recall']:<8.4f} | {m_val['f1_score']:<8.4f} | {m_val['roc_auc']:<8.4f} | {m_val.get('pr_auc', 0.0):<8.4f}")
        print("  " + "-" * 76)

    print("\n  TOP 5 HIGHEST RISK ACCOUNTS:")
    for a in top_risky:
        print(f"    - Account: {a.account_id:<12} | Risk Score: {a.current_risk_score:5.1f} | Level: {a.current_risk_level}")

    print("\n  NEXT STEPS:")
    print("  1. Start Backend API : cd backend && uvicorn app.main:app --port 8000 --reload")
    print("  2. Start Frontend UI : cd frontend && npm run dev")
    print("  3. View Dashboard    : http://localhost:3000")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GraphGuard IBM AML Pipeline Setup & Model Training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Note on sampling and class balance:\n"
            "  The IBM LI-Small dataset has 6.9M transactions with 3,565 laundering events (0.0515%).\n"
            "  Because events are chronologically sorted, the first 100,000 rows contain only 4 positive accounts.\n"
            "  - For genuine ML training (>= 8 positive accounts): use --sample-rows 200000 or larger.\n"
            "  - For data preparation without ML training: use --sample-rows 100000 --allow-insufficient-labels.\n"
            "  - --sample-rows specifies input ingestion limit; --max-db-txs limits rows stored in SQLite."
        )
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=50000,
        help="Number of IBM transactions to sample for pipeline ingestion & ML training (default: 50,000; 0 = all 6.9M rows). Use 200,000+ for >= 8 positive accounts."
    )
    parser.add_argument(
        "--force-recompute",
        action="store_true",
        help="Force recomputation bypassing Parquet cache"
    )
    parser.add_argument(
        "--max-db-txs",
        type=int,
        default=25000,
        help="Max transactions to index in SQLite transactions table (default: 25,000; 0 = all sampled transactions). Prevents local database bloat while full transaction graph is preserved in NetworkX."
    )
    parser.add_argument(
        "--transactions-file",
        help="IBM transaction CSV filename in IBM_DATA_DIR (for example LI-Small_Trans.csv or HI-Small_Trans.csv)"
    )
    parser.add_argument(
        "--accounts-file",
        help="IBM accounts CSV filename in IBM_DATA_DIR"
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Replace generated pipeline records; preserves users and audit logs"
    )
    parser.add_argument(
        "--allow-insufficient-labels",
        action="store_true",
        help="Allow pipeline to complete data preparation and EWS/Graph risk scoring if ground-truth positive labels are insufficient for reliable ML model training"
    )
    parser.add_argument(
        "--min-positives",
        type=int,
        default=8,
        help="Minimum positive labels per class required for stratified holdout evaluation (default: 8)"
    )
    args = parser.parse_args()

    if args.transactions_file:
        settings.IBM_TRANSACTIONS_FILE = args.transactions_file
    if args.accounts_file:
        settings.IBM_ACCOUNTS_FILE = args.accounts_file

    setup_ibm_pipeline(
        sample_rows=args.sample_rows,
        force_recompute=args.force_recompute,
        max_db_txs=args.max_db_txs,
        reset_db=args.reset_db,
        allow_insufficient_labels=args.allow_insufficient_labels,
        min_positives=args.min_positives,
    )
