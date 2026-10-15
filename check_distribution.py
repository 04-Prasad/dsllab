import pandas as pd

path = "data/LI-Small_Trans.csv"
chunk_size = 500_000
start = 0

print("Laundering distribution across the dataset:\n")

for chunk in pd.read_csv(
    path,
    usecols=["Is Laundering"],
    chunksize=chunk_size
):
    labels = pd.to_numeric(chunk["Is Laundering"], errors="coerce")
    positive = int((labels == 1).sum())
    end = start + len(chunk)

    print(
        f"Rows {start + 1:,}-{end:,}: "
        f"{positive:,} laundering transactions"
    )

    start = end
