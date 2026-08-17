"""
GraphGuard Synthetic Data Generator
Generates realistic financial accounts and transaction graph datasets with injected fraud scenarios.
"""

import os
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

def generate_dataset(
    num_normal_accounts=1000,
    num_normal_transactions=8000,
    output_dir="data/generated"
):
    os.makedirs(output_dir, exist_ok=True)
    
    base_time = datetime(2026, 2, 1, 0, 0, 0)
    end_time = datetime(2026, 2, 28, 23, 59, 59)
    total_seconds = int((end_time - base_time).total_seconds())

    accounts = []
    transactions = []

    # 1. Generate Normal Accounts
    for i in range(1, num_normal_accounts + 1):
        acc_id = f"A{i:04d}"
        created_at = base_time - timedelta(days=random.randint(30, 730))
        accounts.append({
            "account_id": acc_id,
            "account_created_at": created_at.isoformat(),
            "account_type": random.choice(["SAVINGS", "CURRENT", "SALARY"]),
            "status": "ACTIVE",
            "label": 0
        })

    account_ids = [a["account_id"] for a in accounts]

    # 2. Generate Normal Transactions
    tx_counter = 1
    for _ in range(num_normal_transactions):
        sender, receiver = random.sample(account_ids, 2)
        random_secs = random.randint(0, total_seconds)
        tx_time = base_time + timedelta(seconds=random_secs)
        amount = round(random.uniform(500, 15000), 2)
        
        transactions.append({
            "transaction_id": f"TX{tx_counter:06d}",
            "sender_account_id": sender,
            "receiver_account_id": receiver,
            "amount": amount,
            "timestamp": tx_time.isoformat(),
            "transaction_type": random.choice(["TRANSFER", "UPI", "NEFT", "IMPS"]),
            "channel": random.choice(["MOBILE_APP", "NET_BANKING", "ATM"]),
            "status": "SUCCESS",
            "label": 0
        })
        tx_counter += 1

    # 3. Inject Demo Scenarios

    # --- Scenario B & C: Fan-In & Rapid Movement Mule Account (A102) ---
    mule_acc = "A102"
    # Ensure A102 exists in accounts list with label 1
    accounts = [a for a in accounts if a["account_id"] != mule_acc]
    accounts.append({
        "account_id": mule_acc,
        "account_created_at": (base_time - timedelta(days=45)).isoformat(),
        "account_type": "SAVINGS",
        "status": "ACTIVE",
        "label": 1
    })

    fanin_senders = []
    fanin_start = datetime(2026, 2, 15, 14, 0, 0)
    for i in range(1, 36): # 35 unique senders
        sender_id = f"A2{i:02d}"
        fanin_senders.append(sender_id)
        if not any(a["account_id"] == sender_id for a in accounts):
            accounts.append({
                "account_id": sender_id,
                "account_created_at": (base_time - timedelta(days=60)).isoformat(),
                "account_type": "SAVINGS",
                "status": "ACTIVE",
                "label": 0
            })
        
        tx_time = fanin_start + timedelta(seconds=random.randint(0, 1200)) # within 20 mins
        amount = round(random.uniform(9200, 9800), 2) # ~9500
        transactions.append({
            "transaction_id": f"TX{tx_counter:06d}",
            "sender_account_id": sender_id,
            "receiver_account_id": mule_acc,
            "amount": amount,
            "timestamp": tx_time.isoformat(),
            "transaction_type": "UPI",
            "channel": "MOBILE_APP",
            "status": "SUCCESS",
            "label": 1
        })
        tx_counter += 1

    # Rapid movement out from A102
    dest_acc_1, dest_acc_2 = "A301", "A302"
    for d in [dest_acc_1, dest_acc_2]:
        if not any(a["account_id"] == d for a in accounts):
            accounts.append({
                "account_id": d,
                "account_created_at": (base_time - timedelta(days=10)).isoformat(),
                "account_type": "CURRENT",
                "status": "ACTIVE",
                "label": 1
            })

    rapid_out_time = fanin_start + timedelta(minutes=25)
    transactions.append({
        "transaction_id": f"TX{tx_counter:06d}",
        "sender_account_id": mule_acc,
        "receiver_account_id": dest_acc_1,
        "amount": 160000.00,
        "timestamp": rapid_out_time.isoformat(),
        "transaction_type": "IMPS",
        "channel": "NET_BANKING",
        "status": "SUCCESS",
        "label": 1
    })
    tx_counter += 1

    transactions.append({
        "transaction_id": f"TX{tx_counter:06d}",
        "sender_account_id": mule_acc,
        "receiver_account_id": dest_acc_2,
        "amount": 145000.00,
        "timestamp": (rapid_out_time + timedelta(minutes=5)).isoformat(),
        "transaction_type": "IMPS",
        "channel": "NET_BANKING",
        "status": "SUCCESS",
        "label": 1
    })
    tx_counter += 1

    # --- Scenario D: Dormancy Burst (A450) ---
    dormant_acc = "A450"
    accounts = [a for a in accounts if a["account_id"] != dormant_acc]
    accounts.append({
        "account_id": dormant_acc,
        "account_created_at": (base_time - timedelta(days=120)).isoformat(),
        "account_type": "SAVINGS",
        "status": "ACTIVE",
        "label": 1
    })

    # Dormancy: only 1 old transaction 90 days ago
    old_tx_time = base_time - timedelta(days=85)
    transactions.append({
        "transaction_id": f"TX{tx_counter:06d}",
        "sender_account_id": dormant_acc,
        "receiver_account_id": "A0001",
        "amount": 500.00,
        "timestamp": old_tx_time.isoformat(),
        "transaction_type": "UPI",
        "channel": "MOBILE_APP",
        "status": "SUCCESS",
        "label": 0
    })
    tx_counter += 1

    # Sudden burst: 25 txns in 1 hour on Feb 18
    burst_start = datetime(2026, 2, 18, 16, 0, 0)
    for b in range(25):
        target = random.choice(account_ids[:50])
        tx_time = burst_start + timedelta(minutes=random.randint(0, 55))
        transactions.append({
            "transaction_id": f"TX{tx_counter:06d}",
            "sender_account_id": dormant_acc,
            "receiver_account_id": target,
            "amount": round(random.uniform(25000, 48000), 2),
            "timestamp": tx_time.isoformat(),
            "transaction_type": "IMPS",
            "channel": "NET_BANKING",
            "status": "SUCCESS",
            "label": 1
        })
        tx_counter += 1

    # --- Scenario E: Fan-Out Account (A500) ---
    fanout_acc = "A500"
    accounts = [a for a in accounts if a["account_id"] != fanout_acc]
    accounts.append({
        "account_id": fanout_acc,
        "account_created_at": (base_time - timedelta(days=90)).isoformat(),
        "account_type": "SAVINGS",
        "status": "ACTIVE",
        "label": 1
    })

    fanout_time = datetime(2026, 2, 20, 10, 0, 0)
    for i in range(1, 21):
        rcv_id = f"A5{i:02d}"
        if not any(a["account_id"] == rcv_id for a in accounts):
            accounts.append({
                "account_id": rcv_id,
                "account_created_at": (base_time - timedelta(days=30)).isoformat(),
                "account_type": "SAVINGS",
                "status": "ACTIVE",
                "label": 0
            })
        tx_time = fanout_time + timedelta(minutes=random.randint(0, 25))
        transactions.append({
            "transaction_id": f"TX{tx_counter:06d}",
            "sender_account_id": fanout_acc,
            "receiver_account_id": rcv_id,
            "amount": 12000.00,
            "timestamp": tx_time.isoformat(),
            "transaction_type": "UPI",
            "channel": "MOBILE_APP",
            "status": "SUCCESS",
            "label": 1
        })
        tx_counter += 1

    # --- Scenario F: Circular Flow (A601 -> A602 -> A603 -> A604 -> A601) ---
    ring = ["A601", "A602", "A603", "A604"]
    for node in ring:
        if not any(a["account_id"] == node for a in accounts):
            accounts.append({
                "account_id": node,
                "account_created_at": (base_time - timedelta(days=50)).isoformat(),
                "account_type": "CURRENT",
                "status": "ACTIVE",
                "label": 1
            })

    ring_start = datetime(2026, 2, 22, 11, 0, 0)
    for idx in range(len(ring)):
        s_node = ring[idx]
        r_node = ring[(idx + 1) % len(ring)]
        tx_time = ring_start + timedelta(minutes=idx * 10)
        transactions.append({
            "transaction_id": f"TX{tx_counter:06d}",
            "sender_account_id": s_node,
            "receiver_account_id": r_node,
            "amount": 150000.00,
            "timestamp": tx_time.isoformat(),
            "transaction_type": "NEFT",
            "channel": "NET_BANKING",
            "status": "SUCCESS",
            "label": 1
        })
        tx_counter += 1

    # --- Scenario G: Suspicious Neighbor (A700) ---
    neighbor_acc = "A700"
    accounts = [a for a in accounts if a["account_id"] != neighbor_acc]
    accounts.append({
        "account_id": neighbor_acc,
        "account_created_at": (base_time - timedelta(days=80)).isoformat(),
        "account_type": "SAVINGS",
        "status": "ACTIVE",
        "label": 1
    })

    high_risk_targets = ["A102", "A301", "A500", "A601"]
    for idx, target in enumerate(high_risk_targets):
        tx_time = datetime(2026, 2, 24, 14, 0, 0) + timedelta(hours=idx)
        transactions.append({
            "transaction_id": f"TX{tx_counter:06d}",
            "sender_account_id": neighbor_acc,
            "receiver_account_id": target,
            "amount": 45000.00,
            "timestamp": tx_time.isoformat(),
            "transaction_type": "TRANSFER",
            "channel": "MOBILE_APP",
            "status": "SUCCESS",
            "label": 1
        })
        tx_counter += 1

    df_accounts = pd.DataFrame(accounts).drop_duplicates(subset=["account_id"])
    df_transactions = pd.DataFrame(transactions)

    acc_path = os.path.join(output_dir, "accounts.csv")
    tx_path = os.path.join(output_dir, "transactions.csv")

    df_accounts.to_csv(acc_path, index=False)
    df_transactions.to_csv(tx_path, index=False)

    print(f"[Data Generator] Saved {len(df_accounts)} accounts to {acc_path}")
    print(f"[Data Generator] Saved {len(df_transactions)} transactions to {tx_path}")

    return df_accounts, df_transactions

if __name__ == "__main__":
    generate_dataset()
