import os
from datetime import datetime, date
from typing import List, Optional, Dict, Any, TypedDict, Tuple
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL", "")

class User(TypedDict):
    id: int
    name: str

class Expense(TypedDict):
    id: int
    spent_at: str
    amount: float
    payer_user_id: int
    category: str
    description: str
    split_json: str

class Settlement(TypedDict):
    month: str
    from_user_id: int
    to_user_id: int
    amount: float
    paid_at: Optional[str]

def get_connection():
    """Establishes a connection to the PostgreSQL database."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não definida. Configure no seu ambiente.")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db() -> None:
    """Initializes the database schema if it doesn't exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL,
                    spent_at DATE NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    payer_user_id INTEGER NOT NULL REFERENCES users(id),
                    category TEXT NOT NULL,
                    description TEXT,
                    split_json TEXT NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settlements (
                    id SERIAL PRIMARY KEY,
                    month TEXT NOT NULL UNIQUE,
                    from_user_id INTEGER NOT NULL REFERENCES users(id),
                    to_user_id INTEGER NOT NULL REFERENCES users(id),
                    amount_cents INTEGER NOT NULL,
                    paid_at TIMESTAMPTZ
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                );
            """)
        conn.commit()

def upsert_default_users(user_a_name: str = "Thiago", user_b_name: str = "Marina") -> None:
    """Creates default users if the table is empty."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users;")
            count = cur.fetchone()["count"]
            if count == 0:
                cur.execute("INSERT INTO users(name) VALUES (%s);", (user_a_name,))
                cur.execute("INSERT INTO users(name) VALUES (%s);", (user_b_name,))
        conn.commit()

def get_users() -> List[User]:
    """Returns a list of all users."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM users ORDER BY id ASC;")
            return cur.fetchall()

def upsert_default_categories() -> None:
    """Seeds default categories, ensuring all defaults exist."""
    defaults = ["Outro", "Mercado", "Contas", "Transporte", "Casa", "Pets"]
    with get_connection() as conn:
        with conn.cursor() as cur:
            for cat in defaults:
                cur.execute("INSERT INTO categories(name) VALUES (%s) ON CONFLICT DO NOTHING;", (cat,))
        conn.commit()

def get_categories() -> List[str]:
    """Returns a list of all category names."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM categories ORDER BY name ASC;")
            return [r["name"] for r in cur.fetchall()]

def add_category(name: str) -> None:
    """Adds a new category if it doesn't already exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO categories(name) VALUES (%s) ON CONFLICT DO NOTHING;", (name,))
        conn.commit()

def update_category(old_name: str, new_name: str) -> None:
    """Updates a category name and all associated expenses."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Update expenses first (or use a cascade if schema allowed, but this is safer)
            cur.execute("UPDATE expenses SET category=%s WHERE category=%s;", (new_name, old_name))
            # Update category table
            cur.execute("UPDATE categories SET name=%s WHERE name=%s;", (new_name, old_name))
        conn.commit()

def delete_category(name: str) -> None:
    """Deletes a category (expenses will keep the category name as text, but it won't be in the list)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM categories WHERE name=%s;", (name,))
        conn.commit()

def add_expense(
    amount_cents: int,
    payer_user_id: int,
    category: str,
    description: str,
    spent_at: str,
    split_json: str
) -> None:
    """Adds a new expense to the database."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO expenses(created_at, spent_at, amount_cents, payer_user_id, category, description, split_json)
                   VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                (datetime.utcnow(), spent_at, amount_cents, payer_user_id, category, description, split_json)
            )
        conn.commit()

def list_expenses_month(month_yyyy_mm: str) -> List[Expense]:
    """Lists all expenses for a given month (YYYY-MM)."""
    year, month = map(int, month_yyyy_mm.split("-"))
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, spent_at, amount_cents, payer_user_id, category, COALESCE(description,'') as description, split_json
                   FROM expenses
                   WHERE spent_at >= %s AND spent_at < %s
                   ORDER BY spent_at DESC, id DESC;""",
                (start, end)
            )
            rows = cur.fetchall()

    return [
        {
            **r,
            "spent_at": str(r["spent_at"]),
            "amount": r["amount_cents"] / 100.0
        }
        for r in rows
    ]

def add_settlement(month: str, from_user_id: int, to_user_id: int, amount_cents: int) -> None:
    """Registers a monthly settlement."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO settlements(month, from_user_id, to_user_id, amount_cents, paid_at)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT(month) DO UPDATE SET
                   from_user_id=EXCLUDED.from_user_id,
                   to_user_id=EXCLUDED.to_user_id,
                   amount_cents=EXCLUDED.amount_cents,
                   paid_at=EXCLUDED.paid_at;""",
                (month, from_user_id, to_user_id, amount_cents, datetime.utcnow())
            )
        conn.commit()

def get_settlement(month: str) -> Optional[Settlement]:
    """Retrieves settlement info for a month."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT month, from_user_id, to_user_id, amount_cents, paid_at FROM settlements WHERE month=%s;",
                (month,)
            )
            r = cur.fetchone()
            if not r:
                return None
            return {
                "month": r["month"],
                "from_user_id": r["from_user_id"],
                "to_user_id": r["to_user_id"],
                "amount": r["amount_cents"] / 100.0,
                "paid_at": r["paid_at"].isoformat() if r["paid_at"] else None
            }

def update_expense(
    expense_id: int,
    amount_cents: int,
    payer_user_id: int,
    category: str,
    description: str,
    spent_at: str,
    split_json: str
) -> None:
    """Updates an existing expense."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE expenses 
                   SET amount_cents=%s, payer_user_id=%s, category=%s, description=%s, spent_at=%s, split_json=%s
                   WHERE id=%s;""",
                (amount_cents, payer_user_id, category, description, spent_at, split_json, expense_id)
            )
        conn.commit()

def delete_expense(expense_id: int) -> None:
    """Deletes an expense from the database."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM expenses WHERE id=%s;", (expense_id,))
        conn.commit()
