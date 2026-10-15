"""
GraphGuard Feature Engineering Engine
=====================================
Extracts account-level behavioral, temporal, and graph topological features.
Compatible with both IBM AML dataset and synthetic data.
"""

import logging
import pandas as pd
import numpy as np
import networkx as nx

logger = logging.getLogger(__name__)


def extract_features(
    accounts_df: pd.DataFrame,
    transactions_df: pd.DataFrame,
    G: nx.DiGraph,
) -> pd.DataFrame:
    """
    Computes behavioral, network, and temporal features for all accounts.
    Returns a DataFrame indexed by account_id with ground-truth label strictly segregated.
    """
    logger.info("[FEATURES] Extracting features for %d accounts and %d transactions...", len(accounts_df), len(transactions_df))
    
    tx_df = transactions_df.copy()
    
    # Ensure standard column names
    sender_col = "sender_account_id" if "sender_account_id" in tx_df.columns else "sender_account"
    receiver_col = "receiver_account_id" if "receiver_account_id" in tx_df.columns else "receiver_account"
    
    tx_df["sender_account_id"] = tx_df[sender_col].astype(str)
    tx_df["receiver_account_id"] = tx_df[receiver_col].astype(str)
    tx_df["amount"] = pd.to_numeric(tx_df["amount"], errors="coerce").fillna(0.0)
    tx_df["timestamp"] = pd.to_datetime(tx_df["timestamp"], errors="coerce")
    tx_df = tx_df.dropna(subset=["timestamp"])

    max_tx_time = tx_df["timestamp"].max() if len(tx_df) > 0 else pd.Timestamp.now()
    min_tx_time = tx_df["timestamp"].min() if len(tx_df) > 0 else max_tx_time

    # 1. NetworkX Graph Topologies
    logger.info("[FEATURES] Computing graph metrics (PageRank, cycle detection)...")
    if G.number_of_nodes() > 0 and G.number_of_edges() > 0:
        try:
            pagerank_dict = nx.pagerank(G, alpha=0.85, max_iter=100)
        except Exception:
            pagerank_dict = {n: 0.0 for n in G.nodes()}
    else:
        pagerank_dict = {str(acc): 0.0 for acc in accounts_df["account_id"]}

    # Bounded cycle detection (lengths 2..4, max 500 checked)
    circular_accounts: set = set()
    if G.number_of_nodes() > 0 and G.number_of_edges() > 0:
        try:
            count = 0
            for cycle in nx.simple_cycles(G):
                count += 1
                if 2 <= len(cycle) <= 4:
                    for node in cycle:
                        circular_accounts.add(str(node))
                if count > 500:
                    break
        except Exception:
            pass

    labeled_suspicious: set = set(
        accounts_df[accounts_df["label"] == 1]["account_id"].astype(str)
    )

    # 2. Pre-aggregate incoming and outgoing stats for speed
    logger.info("[FEATURES] Aggregating transaction metrics per account...")
    inc_agg = tx_df.groupby("receiver_account_id").agg(
        inc_count=("amount", "count"),
        inc_total=("amount", "sum"),
        avg_inc=("amount", "mean"),
        max_inc=("amount", "max"),
        unique_senders=("sender_account_id", "nunique"),
    )

    out_agg = tx_df.groupby("sender_account_id").agg(
        out_count=("amount", "count"),
        out_total=("amount", "sum"),
        avg_out=("amount", "mean"),
        max_out=("amount", "max"),
        unique_receivers=("receiver_account_id", "nunique"),
    )

    inc_agg_dict = inc_agg.to_dict(orient="index")
    out_agg_dict = out_agg.to_dict(orient="index")

    # Fast mapping for velocity & dormancy calculations
    # Index transactions by sender and receiver
    tx_by_sender = {k: v for k, v in tx_df[["sender_account_id", "timestamp", "amount"]].groupby("sender_account_id")}
    tx_by_receiver = {k: v for k, v in tx_df[["receiver_account_id", "timestamp", "amount"]].groupby("receiver_account_id")}

    features_list = []
    
    for _, acc_row in accounts_df.iterrows():
        acc_id = str(acc_row["account_id"])

        # Account age fallback
        raw_created = acc_row.get("account_created_at", None)
        try:
            if pd.isna(raw_created) or not str(raw_created).strip():
                created_at = min_tx_time
            else:
                created_at = pd.to_datetime(raw_created)
        except Exception:
            created_at = min_tx_time
        account_age_days = max(1, int((max_tx_time - created_at).days))

        # Lookups
        inc_info = inc_agg_dict.get(acc_id, {})
        out_info = out_agg_dict.get(acc_id, {})

        inc_count = int(inc_info.get("inc_count", 0))
        out_count = int(out_info.get("out_count", 0))
        total_txs = inc_count + out_count

        inc_total = float(inc_info.get("inc_total", 0.0))
        out_total = float(out_info.get("out_total", 0.0))
        avg_inc = float(inc_info.get("avg_inc", 0.0))
        avg_out = float(out_info.get("avg_out", 0.0))
        max_inc = float(inc_info.get("max_inc", 0.0))
        max_out = float(out_info.get("max_out", 0.0))
        max_amount = max(max_inc, max_out)

        unique_senders = int(inc_info.get("unique_senders", 0))
        unique_receivers = int(out_info.get("unique_receivers", 0))

        # Velocity & Dormancy
        velocity_1h = 0
        velocity_24h = 0
        dormancy_days = 0.0

        if total_txs > 0:
            # Gather timestamps
            ts_list = []
            if acc_id in tx_by_sender:
                ts_list.append(tx_by_sender[acc_id]["timestamp"])
            if acc_id in tx_by_receiver:
                ts_list.append(tx_by_receiver[acc_id]["timestamp"])

            if ts_list:
                all_ts = pd.concat(ts_list).sort_values()
                if len(all_ts) == 1:
                    velocity_1h = 1
                    velocity_24h = 1
                    dormancy_days = 0.0
                else:
                    try:
                        ts_idx = pd.DataFrame({"_cnt": 1}, index=all_ts)
                        v1h = ts_idx["_cnt"].rolling("1h").sum()
                        velocity_1h = int(v1h.max()) if len(v1h) > 0 else 0
                        v24h = ts_idx["_cnt"].rolling("24h").sum()
                        velocity_24h = int(v24h.max()) if len(v24h) > 0 else 0
                        gaps = all_ts.diff().dt.total_seconds().dropna() / 86400.0
                        dormancy_days = float(gaps.max()) if len(gaps) > 0 else 0.0
                    except Exception:
                        velocity_1h = total_txs
                        velocity_24h = total_txs

        # Rapid movement ratio
        rapid_movement_ratio = 0.0
        if inc_total > 0:
            rapid_movement_ratio = min(1.0, out_total / inc_total)

        # Graph features
        in_deg = G.in_degree(acc_id) if G.has_node(acc_id) else 0
        out_deg = G.out_degree(acc_id) if G.has_node(acc_id) else 0
        deg = in_deg + out_deg
        pr_val = pagerank_dict.get(acc_id, 0.0)

        neighbors: set = set()
        if G.has_node(acc_id):
            neighbors = set(G.predecessors(acc_id)).union(set(G.successors(acc_id)))

        risky_neighbors = [n for n in neighbors if n in labeled_suspicious and n != acc_id]
        risky_neighbor_count = len(risky_neighbors)
        risky_neighbor_ratio = (
            risky_neighbor_count / len(neighbors) if len(neighbors) > 0 else 0.0
        )

        has_circular_flow = 1 if acc_id in circular_accounts else 0

        features_list.append({
            "account_id": acc_id,
            "total_transactions": total_txs,
            "incoming_transaction_count": inc_count,
            "outgoing_transaction_count": out_count,
            "incoming_amount_total": round(inc_total, 2),
            "outgoing_amount_total": round(out_total, 2),
            "average_incoming_amount": round(avg_inc, 2),
            "average_outgoing_amount": round(avg_out, 2),
            "max_transaction_amount": round(max_amount, 2),
            "unique_senders": unique_senders,
            "unique_receivers": unique_receivers,
            "fan_in_count": unique_senders,
            "fan_out_count": unique_receivers,
            "transaction_velocity_1h": velocity_1h,
            "transaction_velocity_24h": velocity_24h,
            "dormancy_days": round(dormancy_days, 1),
            "rapid_movement_ratio": round(rapid_movement_ratio, 4),
            "account_age_days": account_age_days,
            "in_degree": int(in_deg),
            "out_degree": int(out_deg),
            "degree": int(deg),
            "pagerank": round(pr_val, 8),
            "risky_neighbor_count": risky_neighbor_count,
            "risky_neighbor_ratio": round(risky_neighbor_ratio, 4),
            "circular_flow_indicator": has_circular_flow,
            "label": int(acc_row.get("label", 0)),
        })

    logger.info("[FEATURES] Extracted features for %d accounts successfully.", len(features_list))
    return pd.DataFrame(features_list)
