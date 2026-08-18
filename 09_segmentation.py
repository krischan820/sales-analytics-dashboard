"""RFM (Recency, Frequency, Monetary) customer segmentation using KMeans.

Reads data/processed/sales.db, computes per-customer RFM metrics, clusters
customers into 4 segments, and labels each cluster by its RFM profile:
Champions, Loyal / Mid-Value, At Risk, New / Low-Value.
Writes results to data/processed/customer_segments.csv.
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "processed" / "sales.db"
OUT_PATH = ROOT / "data" / "processed" / "customer_segments.csv"
N_CLUSTERS = 4
RANDOM_STATE = 42

SEGMENT_LABELS = ["Champions", "Loyal Mid-Value", "At Risk", "New / Low-Value"]


def load_rfm():
    conn = sqlite3.connect(DB_PATH)
    query = """
        WITH last_order_date AS (SELECT MAX(order_date) AS max_date FROM orders)
        SELECT
            o.customer_id,
            CAST(julianday((SELECT max_date FROM last_order_date)) - julianday(MAX(o.order_date)) AS INTEGER) AS recency_days,
            COUNT(DISTINCT o.order_id) AS frequency,
            SUM(oi.net_amount) AS monetary
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        GROUP BY o.customer_id
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


def label_clusters(rfm_df, cluster_col="cluster"):
    """Rank clusters by an RFM score (low recency + high frequency + high
    monetary is best) and map them onto human-readable segment names.
    """
    profile = rfm_df.groupby(cluster_col)[["recency_days", "frequency", "monetary"]].mean()
    # Higher score = better customer: reward frequency/monetary, penalize recency.
    profile["score"] = (
        profile["frequency"].rank()
        + profile["monetary"].rank()
        - profile["recency_days"].rank()
    )
    ranked_clusters = profile.sort_values("score", ascending=False).index.tolist()
    label_map = {cluster: SEGMENT_LABELS[i] for i, cluster in enumerate(ranked_clusters)}
    return label_map


def main():
    rfm = load_rfm()

    features = rfm[["recency_days", "frequency", "monetary"]].copy()
    # Monetary and frequency are right-skewed; log-transform stabilizes clustering.
    features["monetary"] = np.log1p(features["monetary"])
    features["frequency"] = np.log1p(features["frequency"])

    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)

    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
    rfm["cluster"] = kmeans.fit_predict(scaled)

    label_map = label_clusters(rfm)
    rfm["segment"] = rfm["cluster"].map(label_map)
    rfm["monetary"] = rfm["monetary"].round(2)

    rfm = rfm.drop(columns=["cluster"])
    rfm.to_csv(OUT_PATH, index=False)

    print(f"Wrote {len(rfm):,} customer segments to {OUT_PATH}\n")
    summary = rfm.groupby("segment").agg(
        customers=("customer_id", "count"),
        avg_recency_days=("recency_days", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
    ).round(1)
    print(summary.sort_values("avg_monetary", ascending=False))


if __name__ == "__main__":
    main()
