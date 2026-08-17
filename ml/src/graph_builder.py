"""
GraphGuard Graph Construction Engine
Builds directed graph structures using NetworkX from account and transaction DataFrames.
"""

import networkx as nx
import pandas as pd

def build_networkx_graph(accounts_df: pd.DataFrame, transactions_df: pd.DataFrame) -> nx.DiGraph:
    """
    Constructs a directed graph where Accounts are Nodes and Transactions are Edges.
    """
    G = nx.DiGraph()

    # Add Account Nodes
    for _, row in accounts_df.iterrows():
        G.add_node(
            str(row["account_id"]),
            account_created_at=str(row.get("account_created_at", "")),
            account_type=str(row.get("account_type", "SAVINGS")),
            status=str(row.get("status", "ACTIVE")),
            label=int(row.get("label", 0))
        )

    # Add Transaction Edges
    for _, row in transactions_df.iterrows():
        u = str(row["sender_account_id"])
        v = str(row["receiver_account_id"])

        # Ensure u and v exist as nodes
        if not G.has_node(u):
            G.add_node(u, account_type="UNKNOWN", status="ACTIVE", label=0)
        if not G.has_node(v):
            G.add_node(v, account_type="UNKNOWN", status="ACTIVE", label=0)

        # Aggregate weight and track transaction details
        if G.has_edge(u, v):
            G[u][v]["amount"] += float(row["amount"])
            G[u][v]["count"] += 1
            G[u][v]["tx_ids"].append(str(row["transaction_id"]))
        else:
            G.add_edge(
                u, v,
                amount=float(row["amount"]),
                count=1,
                tx_ids=[str(row["transaction_id"])],
                last_timestamp=str(row["timestamp"])
            )

    return G
