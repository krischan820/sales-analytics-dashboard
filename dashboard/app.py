"""Interactive sales analytics dashboard (Streamlit + Plotly).

Run with: streamlit run dashboard/app.py
On first run (e.g. a fresh Streamlit Community Cloud deploy with no
data/processed/ yet), it builds the pipeline itself: generates the sales
data, loads it into SQLite, runs the forecast, and computes RFM segments.
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

DB_PATH = ROOT / "data" / "processed" / "sales.db"
CSV_PATH = ROOT / "data" / "raw" / "sales_data.csv"
FORECAST_PATH = ROOT / "data" / "processed" / "revenue_forecast.csv"
SEGMENTS_PATH = ROOT / "data" / "processed" / "customer_segments.csv"

st.set_page_config(page_title="Sales Analytics Dashboard", layout="wide")


@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            o.order_id, o.order_date, o.customer_id, c.region,
            p.product_name, p.category, oi.quantity, oi.discount_pct,
            oi.gross_amount, oi.discount_amount, oi.net_amount
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        JOIN customers c ON c.customer_id = o.customer_id
        JOIN products p ON p.product_id = oi.product_id
    """
    df = pd.read_sql(query, conn, parse_dates=["order_date"])
    conn.close()

    forecast_df = pd.read_csv(FORECAST_PATH, parse_dates=["month"])
    segments_df = pd.read_csv(SEGMENTS_PATH)
    return df, forecast_df, segments_df


def bootstrap_pipeline():
    """Build the data pipeline from scratch (used on a fresh deploy that
    has no data/processed/ yet — nothing to click, it just runs once).
    """
    import generate_sales_data
    import load_to_sql
    import forecasting
    import segmentation

    if not CSV_PATH.exists():
        generate_sales_data.main()
    load_to_sql.main()
    forecasting.main()
    segmentation.main()


if not (DB_PATH.exists() and FORECAST_PATH.exists() and SEGMENTS_PATH.exists()):
    with st.spinner("First-time setup: generating sales data and running the analysis…"):
        bootstrap_pipeline()

df, forecast_df, segments_df = load_data()

st.title("📊 Sales Analytics Dashboard")

# --- Sidebar filters -------------------------------------------------------
st.sidebar.header("Filters")

min_date, max_date = df["order_date"].min().date(), df["order_date"].max().date()
date_range = st.sidebar.date_input(
    "Order date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)
regions = st.sidebar.multiselect(
    "Region", options=sorted(df["region"].unique()), default=sorted(df["region"].unique())
)
categories = st.sidebar.multiselect(
    "Category", options=sorted(df["category"].unique()), default=sorted(df["category"].unique())
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered = df[
    (df["order_date"].dt.date >= start_date)
    & (df["order_date"].dt.date <= end_date)
    & (df["region"].isin(regions))
    & (df["category"].isin(categories))
]

if filtered.empty:
    st.warning("No data matches the current filters.")
    st.stop()

# --- KPI cards --------------------------------------------------------------
total_revenue = filtered["net_amount"].sum()
total_orders = filtered["order_id"].nunique()
avg_order_value = total_revenue / total_orders if total_orders else 0
unique_customers = filtered["customer_id"].nunique()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Revenue", f"${total_revenue:,.0f}")
col2.metric("Total Orders", f"{total_orders:,}")
col3.metric("Avg Order Value", f"${avg_order_value:,.2f}")
col4.metric("Unique Customers", f"{unique_customers:,}")

st.divider()

# --- Revenue trend + region / category breakdown ----------------------------
left, right = st.columns([2, 1])

with left:
    st.subheader("Monthly Revenue Trend")
    monthly = (
        filtered.set_index("order_date")["net_amount"]
        .resample("MS")
        .sum()
        .reset_index()
    )
    fig = px.line(monthly, x="order_date", y="net_amount", markers=True)
    fig.update_layout(yaxis_title="Revenue ($)", xaxis_title="Month")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Revenue by Region")
    region_rev = filtered.groupby("region")["net_amount"].sum().sort_values(ascending=False)
    fig = px.pie(region_rev, values="net_amount", names=region_rev.index, hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Revenue by Category")
cat_rev = (
    filtered.groupby("category")["net_amount"].sum().sort_values(ascending=False).reset_index()
)
fig = px.bar(cat_rev, x="category", y="net_amount", color="category")
fig.update_layout(yaxis_title="Revenue ($)", showlegend=False)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Top 10 Products by Revenue")
top_products = (
    filtered.groupby(["product_name", "category"])["net_amount"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)
fig = px.bar(
    top_products.sort_values("net_amount"),
    x="net_amount", y="product_name", color="category", orientation="h",
)
fig.update_layout(xaxis_title="Revenue ($)", yaxis_title="")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Forecast ----------------------------------------------------------------
st.subheader("Revenue Forecast (Holt-Winters)")
forecast_months = st.slider("Months of forecast to show", 1, 6, 6)

hist = forecast_df[forecast_df["type"] == "actual"]
fut = forecast_df[forecast_df["type"] == "forecast"].head(forecast_months)
combined = pd.concat([hist, fut])
fig = px.line(combined, x="month", y="revenue", color="type", markers=True)
fig.update_layout(yaxis_title="Revenue ($)", xaxis_title="Month")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Customer segmentation -----------------------------------------------------
st.subheader("Customer Segmentation (RFM)")

seg_col1, seg_col2 = st.columns([1, 2])

with seg_col1:
    seg_counts = segments_df["segment"].value_counts().reset_index()
    seg_counts.columns = ["segment", "customers"]
    fig = px.pie(seg_counts, values="customers", names="segment", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

with seg_col2:
    fig = px.scatter(
        segments_df, x="frequency", y="monetary", color="segment",
        size="monetary", hover_data=["customer_id", "recency_days"],
        log_y=True,
    )
    fig.update_layout(xaxis_title="Frequency (orders)", yaxis_title="Monetary ($, log scale)")
    st.plotly_chart(fig, use_container_width=True)

st.dataframe(
    segments_df.sort_values("monetary", ascending=False).head(20),
    use_container_width=True,
)
