-- Normalized schema for the sales analytics dashboard.
-- Compatible with both SQLite and PostgreSQL (TEXT dates work as ISO-8601 strings in SQLite).

CREATE TABLE IF NOT EXISTS customers (
    customer_id    TEXT PRIMARY KEY,
    customer_name  TEXT NOT NULL,
    email          TEXT,
    region         TEXT NOT NULL,
    acquired_date  DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name   TEXT NOT NULL UNIQUE,
    category       TEXT NOT NULL,
    unit_price     NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id       TEXT PRIMARY KEY,
    customer_id    TEXT NOT NULL REFERENCES customers(customer_id),
    order_date     DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id         TEXT NOT NULL REFERENCES orders(order_id),
    product_id       INTEGER NOT NULL REFERENCES products(product_id),
    quantity         INTEGER NOT NULL,
    discount_pct     NUMERIC(5, 2) NOT NULL DEFAULT 0,
    gross_amount     NUMERIC(10, 2) NOT NULL,
    discount_amount  NUMERIC(10, 2) NOT NULL DEFAULT 0,
    net_amount       NUMERIC(10, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);
