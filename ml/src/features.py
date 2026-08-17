"""
GraphGuard Feature Engineering Engine
Extracts account-level behavioral and graph features.
"""

import pandas as pd
import numpy as np
import networkx as nx
from datetime import datetime


def extract_features(
    accounts_df: pd.DataFrame,
    transactions_df: pd.DataFrame,
    G: nx.DiGraph,
) -> pd.DataFrame:
    """
    Computes behavioral, network, and temporal features for all accounts.
    Returns a DataFrame indexed by account_id.
    """
    tx_df = transactions_df.copy()
    tx_df["timestamp"] = pd.to_datetime(tx_df["timestamp"], errors="coerce")
    tx_df = tx_df.dropna(subset=["timestamp"])

    # PageRank (skip if graph is empty)
    if G.number_of_nodes() > 0 and G.number_of_edges() > 0:
        try:
            pagerank_dict = nx.pagerank(G, alpha=0.85, max_iter=100)
        except Exception:
            pagerank_dict = {n: 0.0 for n in G.nodes()}
    else:
        pagerank_dict = {n: 0.0 for n in G.nodes()}

    # Bounded short cycle detection (lengths 2..4 only, max 500 cycles checked)
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

    max_tx_time = tx_df["timestamp"].max() if len(tx_df) > 0 else pd.Timestamp.now()

    # Identify all accounts labeled suspicious
    labeled_suspicious: set = set(
        accounts_df[accounts_df["label"] == 1]["account_id"].astype(str)
    )

    # Fast indexing by sender and receiver
    inc_grouped = {k: v for k, v in tx_df.groupby("receiver_account_id")}
    out_grouped = {k: v for k, v in tx_df.groupby("sender_account_id")}

    features_list = []

    for _, acc_row in accounts_df.iterrows():
        acc_id = str(acc_row["account_id"])

        # Account age
        try:
            created_at = pd.to_datetime(acc_row.get("account_created_at", max_tx_time))
        except Exception:
            created_at = max_tx_time
        account_age_days = max(1, int((max_tx_time - created_at).days))

        # Fast dictionary lookup
        inc_txs = inc_grouped.get(acc_id, pd.DataFrame())
        out_txs = out_grouped.get(acc_id, pd.DataFrame())

        inc_count = len(inc_txs)
        out_count = len(out_txs)
        total_txs = inc_count + out_count

        inc_total = float(inc_txs["amount"].sum()) if inc_count > 0 else 0.0
        out_total = float(out_txs["amount"].sum()) if out_count > 0 else 0.0
        avg_inc = inc_total / inc_count if inc_count > 0 else 0.0
        avg_out = out_total / out_count if out_count > 0 else 0.0

        unique_senders = int(inc_txs["sender_account_id"].nunique()) if inc_count > 0 else 0
        unique_receivers = int(out_txs["receiver_account_id"].nunique()) if out_count > 0 else 0

        # Velocity & Max Amount
        velocity_1h = 0
        velocity_24h = 0
        max_amount = 0.0

        if total_txs > 0:
            if inc_count > 0 and out_count > 0:
                all_txs = pd.concat([inc_txs, out_txs])
            elif inc_count > 0:
                all_txs = inc_txs
            else:
                all_txs = out_txs

            max_amount = float(all_txs["amount"].max())

            try:
                all_txs = all_txs.sort_values("timestamp")
                ts_idx = all_txs.set_index("timestamp")
                ts_idx["_cnt"] = 1
                v1h = ts_idx["_cnt"].rolling("1h").sum()
                velocity_1h = int(v1h.max()) if len(v1h) > 0 else 0
                v24h = ts_idx["_cnt"].rolling("24h").sum()
                velocity_24h = int(v24h.max()) if len(v24h) > 0 else 0
            except Exception:
                velocity_1h = total_txs
                velocity_24h = total_txs

        # Dormancy: longest gap between consecutive transactions (days)
        dormancy_days = 0.0
        if total_txs > 1:
            try:
                sorted_times = all_txs["timestamp"].sort_values()
                gaps = sorted_times.diff().dt.total_seconds().dropna() / 86400.0
                dormancy_days = float(gaps.max()) if len(gaps) > 0 else 0.0
            except Exception:
                dormancy_days = 0.0

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

    return pd.DataFrame(features_list)
