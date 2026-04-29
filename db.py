import sqlite3
import json

DB = "helpdesk.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS cases (
        id TEXT PRIMARY KEY,
        data TEXT
    )
    """)

    conn.commit()
    conn.close()


def load_case(cid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT data FROM cases WHERE id=?", (cid,))
    row = c.fetchone()

    conn.close()

    if row:
        return json.loads(row[0])

    return {"history": [], "fixes": []}


def save_case(cid, data):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "INSERT OR REPLACE INTO cases VALUES (?, ?)",
        (cid, json.dumps(data))
    )

    conn.commit()
    conn.close()
