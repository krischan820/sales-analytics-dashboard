"""Load data/raw/sales_data.csv into a normalized SQLite database
(data/processed/sales.db) following sql/schema.sql.
"""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "raw" / "sales_data.csv"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
DB_PATH = ROOT / "data" / "processed" / "sales.db"


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    df = pd.read_csv(CSV_PATH, parse_dates=["order_date"])

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())

    customers = (
        df[["customer_id", "region"]]
        .drop_duplicates(subset="customer_id")
        .copy()
    )
    # customer_name/email/acquired_date aren't repeated per line item in the
    # flat CSV beyond customer_id, so derive a stable stand-in from the id.
    customers["customer_name"] = customers["customer_id"]
    customers["email"] = None
    customers["acquired_date"] = df.groupby("customer_id")["order_date"].min().values
    customers[["customer_id", "customer_name", "email", "region", "acquired_date"]].to_sql(
        "customers", conn, if_exists="append", index=False
    )

    products = df[["product_name", "category", "unit_price"]].drop_duplicates(
        subset="product_name"
    )
    products.to_sql("products", conn, if_exists="append", index=False)
    product_id_map = pd.read_sql("SELECT product_id, product_name FROM products", conn)
    product_id_map = dict(zip(product_id_map["product_name"], product_id_map["product_id"]))

    orders = df[["order_id", "customer_id", "order_date"]].drop_duplicates(subset="order_id")
    orders.to_sql("orders", conn, if_exists="append", index=False)

    order_items = df.copy()
    order_items["product_id"] = order_items["product_name"].map(product_id_map)
    order_items = order_items[
        ["order_id", "product_id", "quantity", "discount_pct", "gross_amount",
         "discount_amount", "net_amount"]
    ]
    order_items.to_sql("order_items", conn, if_exists="append", index=False)

    conn.commit()

    counts = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ["customers", "products", "orders", "order_items"]
    }
    conn.close()

    print(f"Loaded database at {DB_PATH}")
    for table, count in counts.items():
        print(f"  {table}: {count:,} rows")


if __name__ == "__main__":
    main()
