"""Forecast monthly revenue using Holt-Winters exponential smoothing.

Reads data/processed/sales.db, aggregates net revenue by month, fits a
Holt-Winters model with additive trend and seasonality, and writes the
historical + forecasted series to data/processed/revenue_forecast.csv.
"""
import sqlite3
from pathlib import Path

import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "processed" / "sales.db"
OUT_PATH = ROOT / "data" / "processed" / "revenue_forecast.csv"
FORECAST_MONTHS = 6


def load_monthly_revenue():
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT strftime('%Y-%m-01', o.order_date) AS month, SUM(oi.net_amount) AS revenue
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        GROUP BY month
        ORDER BY month
    """
    df = pd.read_sql(query, conn, parse_dates=["month"])
    conn.close()
    series = df.set_index("month")["revenue"]
    series.index = pd.DatetimeIndex(series.index, freq="MS")
    return series


def main():
    series = load_monthly_revenue()

    model = ExponentialSmoothing(
        series,
        trend="add",
        seasonal="add",
        seasonal_periods=12,
        initialization_method="estimated",
    ).fit()

    forecast = model.forecast(FORECAST_MONTHS)

    history_df = series.rename("revenue").reset_index().rename(columns={"index": "month"})
    history_df["type"] = "actual"

    forecast_df = forecast.rename("revenue").reset_index().rename(columns={"index": "month"})
    forecast_df["type"] = "forecast"

    result = pd.concat([history_df, forecast_df], ignore_index=True)
    result["revenue"] = result["revenue"].round(2)
    result.to_csv(OUT_PATH, index=False)

    print(f"Wrote {len(result)} rows ({len(series)} actual, {FORECAST_MONTHS} forecast) to {OUT_PATH}")
    print("\nForecast:")
    print(forecast_df[["month", "revenue"]].to_string(index=False))


if __name__ == "__main__":
    main()
