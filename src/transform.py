
from pathlib import Path
import logging
import re

import pandas as pd

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

DATE_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def clean_column_names(df):
    """Standardize column names to lowercase snake_case."""
    df.columns = [
        re.sub(
            r"_+", "_",
            re.sub(r"[^a-zA-Z0-9]+", "_", str(col).strip().lower())
        ).strip("_")
        for col in df.columns
    ]
    return df


def transform_dataset(file_path):
    """Clean one CSV while preserving meaningful missing values."""
    logging.info("Reading %s", file_path.name)

    df = pd.read_csv(file_path)
    original_rows = len(df)

    df = clean_column_names(df)
    df = df.drop_duplicates().copy()

    # Convert order timestamps only when present.
    if file_path.stem == "olist_orders_dataset":
        for col in DATE_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        if "order_purchase_timestamp" in df.columns:
            df["purchase_year"] = (
                df["order_purchase_timestamp"].dt.year
            )
            df["purchase_month"] = (
                df["order_purchase_timestamp"].dt.month
            )
            df["purchase_day"] = (
                df["order_purchase_timestamp"].dt.day
            )
            df["purchase_weekday"] = (
                df["order_purchase_timestamp"].dt.day_name()
            )

        if {
            "order_delivered_customer_date",
            "order_purchase_timestamp",
        }.issubset(df.columns):
            df["delivery_days"] = (
                df["order_delivered_customer_date"]
                - df["order_purchase_timestamp"]
            ).dt.total_seconds() / 86400

    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = CLEANED_DIR / f"{file_path.stem}_cleaned.csv"
    df.to_csv(output_path, index=False)

    logging.info(
        "%s | rows: %s -> %s | duplicates removed: %s",
        file_path.name,
        original_rows,
        len(df),
        original_rows - len(df),
    )
    logging.info("Missing values by column:\n%s", df.isna().sum())
    logging.info("Saved: %s", output_path)

    return {
        "dataset": file_path.name,
        "original_rows": original_rows,
        "cleaned_rows": len(df),
        "duplicates_removed": original_rows - len(df),
        "missing_cells": int(df.isna().sum().sum()),
    }


def main():
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"Raw data folder not found: {RAW_DIR}")

    csv_files = sorted(RAW_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {RAW_DIR}. "
            "Download and extract the Olist dataset first."
        )

    results = [
        transform_dataset(file_path)
        for file_path in csv_files
    ]

    report = pd.DataFrame(results)
    report_path = CLEANED_DIR / "transformation_report.csv"
    report.to_csv(report_path, index=False)

    logging.info("Transformation complete.")
    logging.info("Report saved: %s", report_path)


if __name__ == "__main__":
    main()
