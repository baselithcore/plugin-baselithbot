INSERT INTO shop.customers (name, email, country) VALUES
  ('Alice Rossi',     'alice@example.com',   'IT'),
  ('Bob Bianchi',     'bob@example.com',     'IT'),
  ('Carla Verdi',     'carla@example.com',   'FR'),
  ('Dario Neri',      'dario@example.com',   'IT'),
  ('Eva Gialli',      'eva@example.com',     'DE'),
  ('Franco Blu',      'franco@example.com',  'IT'),
  ('Greta Rosa',      'greta@example.com',   'ES'),
  ('Hugo Marrone',    'hugo@example.com',    'DE');

INSERT INTO shop.products (sku, title, price, stock) VALUES
  ('SKU-001', 'Laptop 14"',     1299.00, 50),
  ('SKU-002', 'Wireless Mouse',   29.90, 500),
  ('SKU-003', 'Mechanical KB',   149.00, 200),
  ('SKU-004', 'USB-C Hub',        59.00, 300),
  ('SKU-005', '4K Monitor',      449.00, 80);

INSERT INTO shop.orders (customer_id, status, total_amount, placed_at) VALUES
  (1, 'paid',     1299.00, now() - interval '30 days'),
  (1, 'paid',      178.90, now() - interval '20 days'),
  (1, 'paid',      449.00, now() - interval '10 days'),
  (2, 'paid',     1299.00, now() - interval '15 days'),
  (2, 'paid',       29.90, now() - interval '5 days'),
  (3, 'paid',      598.00, now() - interval '40 days'),
  (3, 'paid',      149.00, now() - interval '12 days'),
  (4, 'paid',     2598.00, now() - interval '8 days'),
  (4, 'paid',      449.00, now() - interval '3 days'),
  (5, 'paid',       59.00, now() - interval '2 days'),
  (6, 'pending',   149.00, now() - interval '1 day'),
  (7, 'paid',      299.00, now() - interval '25 days'),
  (8, 'cancelled', 999.00, now() - interval '50 days');

INSERT INTO shop.order_items (order_id, product_id, quantity, unit_price) VALUES
  (1, 1, 1, 1299.00),
  (2, 2, 1,   29.90), (2, 3, 1, 149.00),
  (3, 5, 1,  449.00),
  (4, 1, 1, 1299.00),
  (5, 2, 1,   29.90),
  (6, 4, 2,   59.00), (6, 1, 1, 480.00),
  (7, 3, 1,  149.00),
  (8, 1, 2, 1299.00),
  (9, 5, 1,  449.00),
  (10, 4, 1,   59.00),
  (11, 3, 1,  149.00),
  (12, 1, 1, 299.00);

INSERT INTO shop.payments (order_id, amount, method, paid_at) VALUES
  (1, 1299.00, 'card',     now() - interval '30 days'),
  (2,  178.90, 'card',     now() - interval '20 days'),
  (3,  449.00, 'paypal',   now() - interval '10 days'),
  (4, 1299.00, 'card',     now() - interval '15 days'),
  (5,   29.90, 'card',     now() - interval '5 days'),
  (6,  598.00, 'transfer', now() - interval '40 days'),
  (7,  149.00, 'card',     now() - interval '12 days'),
  (8, 2598.00, 'transfer', now() - interval '8 days'),
  (9,  449.00, 'card',     now() - interval '3 days'),
  (10,  59.00, 'card',     now() - interval '2 days'),
  (12, 299.00, 'card',     now() - interval '25 days');

-- Read-only role for dbview
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'dbview_ro') THEN
    CREATE ROLE dbview_ro LOGIN PASSWORD 'dbview_ro_password';
  END IF;
END$$;

GRANT CONNECT ON DATABASE shopdb TO dbview_ro;
GRANT USAGE ON SCHEMA shop TO dbview_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA shop TO dbview_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA shop GRANT SELECT ON TABLES TO dbview_ro;
