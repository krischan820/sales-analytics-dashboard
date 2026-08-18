"""Generate a synthetic retail sales dataset for the analytics dashboard.

Produces data/raw/sales_data.csv: one row per order line item, with enough
customers/products/regions/seasonality/discount structure to make the KPI,
forecasting, and RFM segmentation logic downstream produce realistic results.
"""
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

RNG_SEED = 42
N_ROWS = 12_000
START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 12, 31)

random.seed(RNG_SEED)
np.random.seed(RNG_SEED)

REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East & Africa"]

PRODUCT_CATALOG = [
    ("Aria Wireless Headphones", "Electronics", 129.99),
    ("Pulse Fitness Tracker", "Electronics", 89.99),
    ("Zenith 4K Monitor", "Electronics", 349.99),
    ("Nimbus Bluetooth Speaker", "Electronics", 59.99),
    ("Vertex Mechanical Keyboard", "Electronics", 99.99),
    ("Comet Office Chair", "Furniture", 219.99),
    ("Summit Standing Desk", "Furniture", 449.99),
    ("Haven Bookshelf", "Furniture", 159.99),
    ("Drift Table Lamp", "Furniture", 44.99),
    ("Cascade Throw Blanket", "Home Goods", 34.99),
    ("Ember Scented Candle Set", "Home Goods", 24.99),
    ("Meadow Ceramic Dinnerware Set", "Home Goods", 79.99),
    ("Tundra Insulated Water Bottle", "Outdoor", 29.99),
    ("Ridge Hiking Backpack", "Outdoor", 119.99),
    ("Solstice Camping Tent", "Outdoor", 199.99),
    ("Pinnacle Yoga Mat", "Sports & Fitness", 39.99),
    ("Torque Adjustable Dumbbells", "Sports & Fitness", 149.99),
    ("Glide Running Shoes", "Sports & Fitness", 89.99),
    ("Quill Leather Notebook", "Office Supplies", 19.99),
    ("Anchor Desk Organizer", "Office Supplies", 27.99),
]

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Wei", "Priya", "Yuki", "Fatima", "Carlos",
    "Sofia", "Ahmed", "Ingrid", "Kenji", "Amara", "Liam", "Olivia", "Noah", "Emma",
    "Lucas", "Mia", "Ethan", "Ava", "Mateo", "Zara",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
]

N_CUSTOMERS = 850


def build_customers(n):
    customers = []
    for i in range(1, n + 1):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        region = random.choices(
            REGIONS, weights=[0.35, 0.28, 0.20, 0.10, 0.07]
        )[0]
        acquired = START_DATE + timedelta(days=random.randint(0, (END_DATE - START_DATE).days - 30))
        customers.append(
            {
                "customer_id": f"CUST-{i:05d}",
                "customer_name": f"{first} {last}",
                "email": f"{first.lower()}.{last.lower()}{i}@example.com",
                "region": region,
                "acquired_date": acquired,
                "segment_hint": random.choices(
                    ["frequent", "occasional", "one_time"], weights=[0.2, 0.5, 0.3]
                )[0],
            }
        )
    return pd.DataFrame(customers)


def seasonal_weight(d: date) -> float:
    """Boost order volume around Q4 holidays and summer, dip in Jan/Feb."""
    month_weights = {
        1: 0.75, 2: 0.8, 3: 0.9, 4: 0.95, 5: 1.0, 6: 1.05,
        7: 1.05, 8: 1.0, 9: 1.0, 10: 1.15, 11: 1.35, 12: 1.5,
    }
    weight = month_weights[d.month]
    # mild year-over-year growth
    year_growth = {2023: 0.9, 2024: 1.0, 2025: 1.12}
    weight *= year_growth.get(d.year, 1.0)
    return weight


def random_order_date():
    days_span = (END_DATE - START_DATE).days
    candidates = []
    for _ in range(30):
        d = START_DATE + timedelta(days=random.randint(0, days_span))
        candidates.append(d)
    weights = [seasonal_weight(d) for d in candidates]
    return random.choices(candidates, weights=weights)[0]


def build_orders_and_items(customers_df, n_rows):
    rows = []
    order_counter = 1
    customer_ids = customers_df["customer_id"].tolist()
    hint_map = dict(zip(customers_df["customer_id"], customers_df["segment_hint"]))
    region_map = dict(zip(customers_df["customer_id"], customers_df["region"]))

    hint_weights = {"frequent": 4.0, "occasional": 1.5, "one_time": 0.4}
    cust_weights = [hint_weights[hint_map[c]] for c in customer_ids]

    rows_generated = 0
    while rows_generated < n_rows:
        customer_id = random.choices(customer_ids, weights=cust_weights)[0]
        order_date = random_order_date()
        order_id = f"ORD-{order_counter:06d}"
        order_counter += 1

        n_items = random.choices([1, 2, 3, 4], weights=[0.55, 0.25, 0.13, 0.07])[0]
        n_items = min(n_items, n_rows - rows_generated)
        chosen_products = random.sample(PRODUCT_CATALOG, k=min(n_items, len(PRODUCT_CATALOG)))

        for product_name, category, unit_price in chosen_products:
            quantity = random.choices([1, 2, 3, 4, 5], weights=[0.5, 0.25, 0.13, 0.07, 0.05])[0]
            discount_pct = random.choices(
                [0.0, 0.05, 0.10, 0.15, 0.20], weights=[0.55, 0.15, 0.15, 0.10, 0.05]
            )[0]
            gross_amount = round(unit_price * quantity, 2)
            discount_amount = round(gross_amount * discount_pct, 2)
            net_amount = round(gross_amount - discount_amount, 2)

            rows.append(
                {
                    "order_id": order_id,
                    "order_date": order_date,
                    "customer_id": customer_id,
                    "region": region_map[customer_id],
                    "product_name": product_name,
                    "category": category,
                    "unit_price": unit_price,
                    "quantity": quantity,
                    "discount_pct": discount_pct,
                    "gross_amount": gross_amount,
                    "discount_amount": discount_amount,
                    "net_amount": net_amount,
                }
            )
            rows_generated += 1
            if rows_generated >= n_rows:
                break

    return pd.DataFrame(rows)


def main():
    customers_df = build_customers(N_CUSTOMERS)
    sales_df = build_orders_and_items(customers_df, N_ROWS)
    sales_df = sales_df.sort_values("order_date").reset_index(drop=True)

    out_path = Path(__file__).resolve().parent.parent / "data" / "raw" / "sales_data.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sales_df.to_csv(out_path, index=False)
    print(f"Wrote {len(sales_df):,} rows to {out_path}")
    print(f"Date range: {sales_df['order_date'].min()} to {sales_df['order_date'].max()}")
    print(f"Unique customers: {sales_df['customer_id'].nunique():,}")
    print(f"Unique orders: {sales_df['order_id'].nunique():,}")


if __name__ == "__main__":
    main()
