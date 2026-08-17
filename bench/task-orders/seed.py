"""Fill the database with development data."""
import random

from db import reset_db

NAMES = ["acme", "globex", "initech", "umbrella", "soylent"]
STATUSES = ["paid", "shipped", "refunded", "pending"]


def seed(rows=250, seed_value=7):
    rng = random.Random(seed_value)
    conn = reset_db()
    for i in range(1, rows + 1):
        conn.execute(
            "INSERT INTO orders (id, customer, amount_cents, status) VALUES (?, ?, ?, ?)",
            (i, rng.choice(NAMES), rng.randrange(100, 100000), rng.choice(STATUSES)),
        )
    conn.commit()
    return conn


if __name__ == "__main__":
    seed()
    print("seeded")
