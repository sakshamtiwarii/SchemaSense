-- Sample schema (products & orders) plus a read-only role for the app to
-- connect as. This is the DB-level backstop behind app/core/safety.py:
-- even if the regex check has a gap, this role physically cannot write.

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    revenue NUMERIC(10, 2) NOT NULL,
    order_date DATE NOT NULL
);

INSERT INTO products (product_name, category, unit_price) VALUES
    ('Widget A', 'Widgets', 19.99),
    ('Widget B', 'Widgets', 24.50),
    ('Gadget X', 'Gadgets', 49.00),
    ('Gadget Y', 'Gadgets', 65.25),
    ('Gizmo Pro', 'Gizmos', 120.00);

INSERT INTO orders (product_id, quantity, revenue, order_date) VALUES
    (1, 10, 199.90, CURRENT_DATE - INTERVAL '10 days'),
    (1, 5, 99.95, CURRENT_DATE - INTERVAL '40 days'),
    (2, 8, 196.00, CURRENT_DATE - INTERVAL '5 days'),
    (3, 3, 147.00, CURRENT_DATE - INTERVAL '20 days'),
    (4, 6, 391.50, CURRENT_DATE - INTERVAL '2 days'),
    (5, 2, 240.00, CURRENT_DATE - INTERVAL '60 days'),
    (5, 1, 120.00, CURRENT_DATE - INTERVAL '1 day'),
    (2, 12, 294.00, CURRENT_DATE - INTERVAL '90 days');

DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'nlsql_app') THEN
        CREATE ROLE nlsql_app WITH LOGIN PASSWORD 'nlsql_app';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE nlsql TO nlsql_app;
GRANT USAGE ON SCHEMA public TO nlsql_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO nlsql_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO nlsql_app;
