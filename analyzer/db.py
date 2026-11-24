"""SQLite storage for transactions (plain sqlite3, no ORM)."""
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bank.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,          -- 'YYYY-MM-DD'
    description TEXT NOT NULL,
    amount      REAL NOT NULL,          -- expenses negative
    category    TEXT NOT NULL,
    UNIQUE (date, description, amount)
);
"""


def get_connection(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db(db_path: str | Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)


def insert_transactions(df: pd.DataFrame, db_path: str | Path = DB_PATH) -> int:
    """Insert rows (date, description, amount, category); return number of new rows."""
    rows = [
        (
            pd.Timestamp(r.date).strftime("%Y-%m-%d"),
            str(r.description),
            round(float(r.amount), 2),
            str(r.category),
        )
        for r in df.itertuples(index=False)
    ]
    conn = get_connection(db_path)
    try:
        before = conn.total_changes
        conn.executemany(
            "INSERT OR IGNORE INTO transactions (date, description, amount, category) "
            "VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        return conn.total_changes - before
    finally:
        conn.close()


def load_all(db_path: str | Path = DB_PATH) -> pd.DataFrame:
    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(
            "SELECT id, date, description, amount, category FROM transactions ORDER BY date",
            conn,
        )
    finally:
        conn.close()
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    return df


def monthly_totals(db_path: str | Path = DB_PATH) -> pd.DataFrame:
    """Income, spent and net per month, aggregated in SQL."""
    query = """
        SELECT substr(date, 1, 7)                                   AS month,
               ROUND(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 2)  AS income,
               ROUND(-SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END), 2) AS spent,
               ROUND(SUM(amount), 2)                                AS net
        FROM transactions
        GROUP BY month
        ORDER BY month
    """
    conn = get_connection(db_path)
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()
