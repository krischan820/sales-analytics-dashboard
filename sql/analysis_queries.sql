-- Analysis queries for the sales analytics dashboard.
-- Run against data/processed/sales.db (SQLite) after `python src/load_to_sql.py`.

-- 1. Headline KPIs: total revenue, total orders, average order value, unique customers.
SELECT
    ROUND(SUM(oi.net_amount), 2)                         AS total_revenue,
    COUNT(DISTINCT oi.order_id)                          AS total_orders,
    ROUND(SUM(oi.net_amount) * 1.0 / COUNT(DISTINCT oi.order_id), 2) AS avg_order_value,
    COUNT(DISTINCT o.customer_id)                        AS unique_customers
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id;

-- 2. Revenue by region.
SELECT
    c.region,
    ROUND(SUM(oi.net_amount), 2) AS revenue,
    COUNT(DISTINCT oi.order_id)  AS orders
FROM order_items oi
JOIN orders o ON o.order_id = oi.order_id
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.region
ORDER BY revenue DESC;

-- 3. Revenue by product category.
SELECT
    p.category,
    ROUND(SUM(oi.net_amount), 2) AS revenue,
    SUM(oi.quantity)             AS units_sold
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY revenue DESC;

-- 4. Month-over-month revenue growth.
WITH monthly AS (
    SELECT
        strftime('%Y-%m', o.order_date) AS month,
        SUM(oi.net_amount)              AS revenue
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    GROUP BY month
)
SELECT
    month,
    ROUND(revenue, 2) AS revenue,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY month)) * 100.0
        / LAG(revenue) OVER (ORDER BY month), 2
    ) AS mom_growth_pct
FROM monthly
ORDER BY month;

-- 5. Top 10 products by revenue.
SELECT
    p.product_name,
    p.category,
    ROUND(SUM(oi.net_amount), 2) AS revenue,
    SUM(oi.quantity)             AS units_sold
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;

-- 6. RFM base metrics per customer (Recency in days from most recent order date in
-- the dataset, Frequency = distinct orders, Monetary = total net spend).
WITH last_order_date AS (
    SELECT MAX(order_date) AS max_date FROM orders
)
SELECT
    o.customer_id,
    CAST(julianday((SELECT max_date FROM last_order_date)) - julianday(MAX(o.order_date)) AS INTEGER) AS recency_days,
    COUNT(DISTINCT o.order_id) AS frequency,
    ROUND(SUM(oi.net_amount), 2) AS monetary
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
GROUP BY o.customer_id
ORDER BY monetary DESC;

-- 7. Average discount rate and its effect on revenue, by category.
SELECT
    p.category,
    ROUND(AVG(oi.discount_pct) * 100, 2) AS avg_discount_pct,
    ROUND(SUM(oi.discount_amount), 2)    AS total_discount_given,
    ROUND(SUM(oi.gross_amount), 2)       AS gross_revenue,
    ROUND(SUM(oi.net_amount), 2)         AS net_revenue
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY total_discount_given DESC;
