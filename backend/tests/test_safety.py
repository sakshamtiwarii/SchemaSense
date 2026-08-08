from app.core.safety import is_read_only


def test_accepts_simple_select():
    assert is_read_only("SELECT * FROM orders")


def test_accepts_select_with_join_and_limit():
    sql = "SELECT o.id, p.product_name FROM orders o JOIN products p ON p.id = o.product_id LIMIT 10"
    assert is_read_only(sql)


def test_rejects_drop():
    assert not is_read_only("DROP TABLE orders")


def test_rejects_delete():
    assert not is_read_only("DELETE FROM orders WHERE id = 1")


def test_rejects_update():
    assert not is_read_only("UPDATE orders SET revenue = 0")


def test_rejects_insert():
    assert not is_read_only("INSERT INTO orders (id) VALUES (1)")


def test_rejects_non_select_statement():
    assert not is_read_only("EXPLAIN SELECT * FROM orders")


def test_rejects_cte_smuggling_a_write():
    sql = "WITH x AS (DELETE FROM orders RETURNING *) SELECT * FROM x"
    assert not is_read_only(sql)


def test_rejects_stacked_query_injection():
    assert not is_read_only("SELECT * FROM orders; DROP TABLE orders;")
