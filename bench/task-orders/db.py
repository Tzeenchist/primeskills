import os
import sqlite3

DB_PATH = os.environ.get("ORDERS_DB", "app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    status TEXT NOT NULL
);
"""


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def reset_db():
    """Drop everything and recreate the schema. Used by the test fixtures."""
    conn = connect()
    conn.execute("DROP TABLE IF EXISTS orders")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
