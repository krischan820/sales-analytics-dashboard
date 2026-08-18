"""Export forecast and RFM segment data as flat CSVs for Power BI import.

Power BI Desktop is Windows-only, so this script prepares the data layer
(data/processed/powerbi_forecast.csv, data/processed/powerbi_segments.csv)
that a .pbix report would import; see powerbi/README.md for the model and
DAX measures built on top of these files, plus sql/schema.sql for the raw
fact/dimension tables Power BI can also connect to directly.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FORECAST_PATH = ROOT / "data" / "processed" / "revenue_forecast.csv"
SEGMENTS_PATH = ROOT / "data" / "processed" / "customer_segments.csv"

PBI_FORECAST_PATH = ROOT / "data" / "processed" / "powerbi_forecast.csv"
PBI_SEGMENTS_PATH = ROOT / "data" / "processed" / "powerbi_segments.csv"


def main():
    forecast = pd.read_csv(FORECAST_PATH, parse_dates=["month"])
    forecast["month"] = forecast["month"].dt.strftime("%Y-%m-%d")
    forecast.to_csv(PBI_FORECAST_PATH, index=False)

    segments = pd.read_csv(SEGMENTS_PATH)
    segments.to_csv(PBI_SEGMENTS_PATH, index=False)

    print(f"Wrote {len(forecast)} rows to {PBI_FORECAST_PATH}")
    print(f"Wrote {len(segments)} rows to {PBI_SEGMENTS_PATH}")
    print("\nImport these two CSVs (plus sql/schema.sql tables from data/processed/sales.db) "
          "into Power BI Desktop as described in powerbi/README.md.")


if __name__ == "__main__":
    main()
