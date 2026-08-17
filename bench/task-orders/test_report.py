from db import reset_db
from report import summary

FIXTURE = [
    (1, "acme", 1000, "paid"),
    (2, "globex", 2500, "shipped"),
    (3, "initech", 700, "refunded"),
    (4, "umbrella", 300, "pending"),
]


def make_db():
    conn = reset_db()
    conn.executemany(
        "INSERT INTO orders (id, customer, amount_cents, status) VALUES (?, ?, ?, ?)",
        FIXTURE,
    )
    conn.commit()
    return conn


def test_counts_billable_orders():
    assert summary(make_db())["orders"] == 2


def test_sums_billable_revenue():
    assert summary(make_db())["revenue_cents"] == 3500


def test_ignores_refunded():
    conn = make_db()
    assert summary(conn)["revenue_cents"] == 3500
