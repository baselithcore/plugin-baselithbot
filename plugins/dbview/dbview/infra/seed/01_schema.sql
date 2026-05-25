-- Demo schema: customers / orders / payments
CREATE SCHEMA IF NOT EXISTS shop;

CREATE TABLE shop.customers (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  email       TEXT NOT NULL UNIQUE,
  country     TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE shop.orders (
  id            SERIAL PRIMARY KEY,
  customer_id   INTEGER NOT NULL REFERENCES shop.customers(id) ON DELETE CASCADE,
  status        TEXT NOT NULL CHECK (status IN ('pending','paid','cancelled','refunded')),
  total_amount  NUMERIC(12,2) NOT NULL,
  placed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON shop.orders(customer_id);

CREATE TABLE shop.payments (
  id          SERIAL PRIMARY KEY,
  order_id    INTEGER NOT NULL REFERENCES shop.orders(id) ON DELETE CASCADE,
  amount      NUMERIC(12,2) NOT NULL,
  method      TEXT NOT NULL,
  paid_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON shop.payments(order_id);

CREATE TABLE shop.products (
  id          SERIAL PRIMARY KEY,
  sku         TEXT NOT NULL UNIQUE,
  title       TEXT NOT NULL,
  price       NUMERIC(12,2) NOT NULL,
  stock       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE shop.order_items (
  id          SERIAL PRIMARY KEY,
  order_id    INTEGER NOT NULL REFERENCES shop.orders(id) ON DELETE CASCADE,
  product_id  INTEGER NOT NULL REFERENCES shop.products(id) ON DELETE RESTRICT,
  quantity    INTEGER NOT NULL CHECK (quantity > 0),
  unit_price  NUMERIC(12,2) NOT NULL
);
CREATE INDEX ON shop.order_items(order_id);
CREATE INDEX ON shop.order_items(product_id);
