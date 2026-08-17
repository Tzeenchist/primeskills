"""Monthly order report."""
from db import connect

BILLABLE = ("paid", "shipped")


def load_orders(conn):
    rows = conn.execute(
        "SELECT id, customer, amount_cents, status FROM orders"
    ).fetchall()
    return {row["customer"]: dict(row) for row in rows}


def billable(orders):
    return [o for o in orders.values() if o["status"] in BILLABLE]


def summary(conn):
    orders = load_orders(conn)
    paid = billable(orders)
    return {
        "orders": len(paid),
        "revenue_cents": sum(o["amount_cents"] for o in paid),
    }
