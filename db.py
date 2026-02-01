import os
import sqlite3
from datetime import datetime

DB = os.getenv("DB_PATH", "casa_split.db")

def conn():
    db_dir = os.path.dirname(DB)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    return sqlite3.connect(DB, check_same_thread=False)


def init_db():
    with conn() as c:
        cur = c.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            spent_at TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            payer_user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            split_json TEXT NOT NULL
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL UNIQUE,
            from_user_id INTEGER NOT NULL,
            to_user_id INTEGER NOT NULL,
            amount_cents INTEGER NOT NULL,
            paid_at TEXT
        )""")
        c.commit()

def upsert_default_users(user_a_name="Thiago", user_b_name="Marina"):
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO users(name) VALUES (?)", (user_a_name,))
            cur.execute("INSERT INTO users(name) VALUES (?)", (user_b_name,))
        c.commit()

def get_users():
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT id, name FROM users ORDER BY id ASC")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1]} for r in rows]

def add_expense(amount_cents, payer_user_id, category, description, spent_at, split_json):
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO expenses(created_at, spent_at, amount_cents, payer_user_id, category, description, split_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(), spent_at, amount_cents, payer_user_id, category, description, split_json)
        )
        c.commit()

def list_expenses_month(month_yyyy_mm: str):
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """SELECT id, spent_at, amount_cents, payer_user_id, category, description, split_json
               FROM expenses
               WHERE spent_at LIKE ?
               ORDER BY spent_at DESC, id DESC""",
            (f"{month_yyyy_mm}%",)
        )
        rows = cur.fetchall()
        out = []
        for r in rows:
            out.append({
                "id": r[0],
                "spent_at": r[1],
                "amount": r[2] / 100.0,
                "payer_user_id": r[3],
                "category": r[4],
                "description": r[5] or "",
                "split_json": r[6]
            })
        return out

def add_settlement(month, from_user_id, to_user_id, amount_cents):
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO settlements(month, from_user_id, to_user_id, amount_cents, paid_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(month) DO UPDATE SET
               from_user_id=excluded.from_user_id,
               to_user_id=excluded.to_user_id,
               amount_cents=excluded.amount_cents,
               paid_at=excluded.paid_at
            """,
            (month, from_user_id, to_user_id, amount_cents, datetime.now().isoformat())
        )
        c.commit()

def get_settlement(month):
    with conn() as c:
        cur = c.cursor()
        cur.execute(
            "SELECT month, from_user_id, to_user_id, amount_cents, paid_at FROM settlements WHERE month=?",
            (month,)
        )
        r = cur.fetchone()
        if not r:
            return None
        return {"month": r[0], "from_user_id": r[1], "to_user_id": r[2], "amount": r[3]/100.0, "paid_at": r[4]}

