import os
from datetime import datetime, date
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL", "")

def conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não definida. Configure no Render e/ou no seu ambiente local.")
    return psycopg.connect(DATABASE_URL)

def init_db():
    with conn() as c:
        with c.cursor() as cur:
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
        c.commit()

def upsert_default_users(user_a_name="Thiago", user_b_name="Marina"):
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users;")
            n = cur.fetchone()[0]
            if n == 0:
                cur.execute("INSERT INTO users(name) VALUES (%s);", (user_a_name,))
                cur.execute("INSERT INTO users(name) VALUES (%s);", (user_b_name,))
        c.commit()

def get_users():
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("SELECT id, name FROM users ORDER BY id ASC;")
            rows = cur.fetchall()
            return [{"id": r[0], "name": r[1]} for r in rows]

def add_expense(amount_cents, payer_user_id, category, description, spent_at, split_json):
    # spent_at chega como "YYYY-MM-DD"
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """INSERT INTO expenses(created_at, spent_at, amount_cents, payer_user_id, category, description, split_json)
                   VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                (datetime.utcnow(), spent_at, amount_cents, payer_user_id, category, description, split_json)
            )
        c.commit()

def list_expenses_month(month_yyyy_mm: str):
    # month_yyyy_mm: "YYYY-MM"
    year, month = month_yyyy_mm.split("-")
    y = int(year)
    m = int(month)
    start = date(y, m, 1)
    if m == 12:
        end = date(y + 1, 1, 1)
    else:
        end = date(y, m + 1, 1)

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """SELECT id, spent_at, amount_cents, payer_user_id, category, COALESCE(description,''), split_json
                   FROM expenses
                   WHERE spent_at >= %s AND spent_at < %s
                   ORDER BY spent_at DESC, id DESC;""",
                (start, end)
            )
            rows = cur.fetchall()

    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "spent_at": str(r[1]),
            "amount": r[2] / 100.0,
            "payer_user_id": r[3],
            "category": r[4],
            "description": r[5],
            "split_json": r[6],
        })
    return out

def add_settlement(month, from_user_id, to_user_id, amount_cents):
    with conn() as c:
        with c.cursor() as cur:
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
        c.commit()

def get_settlement(month):
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT month, from_user_id, to_user_id, amount_cents, paid_at FROM settlements WHERE month=%s;",
                (month,)
            )
            r = cur.fetchone()
            if not r:
                return None
            return {
                "month": r[0],
                "from_user_id": r[1],
                "to_user_id": r[2],
                "amount": r[3] / 100.0,
                "paid_at": r[4].isoformat() if r[4] else None
            }
