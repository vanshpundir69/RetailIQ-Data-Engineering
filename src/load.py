
from pathlib import Path
import logging
import os
import re

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEANED_DIR = PROJECT_ROOT / "data" / "cleaned"

load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# Preserve identifiers such as order_id and customer_id as strings.
ID_COLUMNS = {
    "order_id",
    "customer_id",
    "customer_unique_id",
    "product_id",
    "seller_id",
    "review_id",
    "order_item_id",
    "payment_sequential",
    "zip_code_prefix",
}


def get_engine():
    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [key for key in required if os.getenv(key) is None]

    if missing:
        raise ValueError(
            f"Missing database settings in .env: {', '.join(missing)}"
        )

    url = URL.create(
        "mysql+pymysql",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.environ["DB_NAME"],
        query={"charset": "utf8mb4"},
    )

    return create_engine(url, pool_pre_ping=True)


def table_name_from_file(file_path):
    name = file_path.stem.lower()
    name = re.sub(r"[^a-z0-9_]", "_", name)

    if not name or not name[0].isalpha():
        raise ValueError(f"Invalid table name: {name}")

    return name


def load_csv(engine, file_path):
    table_name = table_name_from_file(file_path)
    logging.info("Loading %s into %s", file_path.name, table_name)

    # Read identifiers as strings to preserve their original values.
    df = pd.read_csv(file_path, dtype="string", low_memory=False)

    # Restore numeric types where appropriate.
    for col in df.columns:
        if col in ID_COLUMNS:
            continue

        if col.endswith("_timestamp"):
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif col in {
            "purchase_year",
            "purchase_month",
            "purchase_day",
            "payment_installments",
        }:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Load in chunks rather than issuing one enormous insert.
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=5000,
        method="multi",
    )

    with engine.connect() as connection:
        count = connection.execute(
            text(f"SELECT COUNT(*) FROM `{table_name}`")
        ).scalar_one()

    logging.info("Loaded %s rows into %s", count, table_name)
    return {"table": table_name, "rows_loaded": count}


def main():
    if not CLEANED_DIR.exists():
        raise FileNotFoundError(
            f"Cleaned data directory not found: {CLEANED_DIR}"
        )

    csv_files = sorted(
        path for path in CLEANED_DIR.glob("*.csv")
        if path.name != "transformation_report.csv"
    )

    if not csv_files:
        raise FileNotFoundError(
            "No cleaned CSV files found. Run transform.py first."
        )

    engine = get_engine()

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        logging.info("Connected to MySQL successfully.")

        results = [
            load_csv(engine, file_path)
            for file_path in csv_files
        ]

        report = pd.DataFrame(results)
        report_path = CLEANED_DIR / "load_report.csv"
        report.to_csv(report_path, index=False)

        logging.info("Load complete. Report saved to %s", report_path)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
