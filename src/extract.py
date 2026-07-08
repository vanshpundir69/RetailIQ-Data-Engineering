import os
import pandas as pd

# Folder containing raw CSV files
DATA_PATH = "data/raw"

print("=" * 60)
print("RetailIQ - Data Extraction")
print("=" * 60)

# Read every CSV in the folder
for file in os.listdir(DATA_PATH):
    if file.endswith(".csv"):

        file_path = os.path.join(DATA_PATH, file)

        df = pd.read_csv(file_path)

        print(f"\n📄 File: {file}")
        print(f"Rows: {df.shape[0]}")
        print(f"Columns: {df.shape[1]}")

        print("\nColumns:")
        print(df.columns.tolist())

        print("\nMissing Values:")
        print(df.isnull().sum())

        print("-" * 60)