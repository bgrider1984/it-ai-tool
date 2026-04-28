import sqlite3
import json
from datetime import datetime

DB_NAME = "helpdesk.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS cases (
        id TEXT PRIMARY KEY,
        created_at TEXT,
        data TEXT
    )
    """)

    conn.commit()
    conn.close()


def load_case(case_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT data FROM cases WHERE id=?", (case_id,))
    row = c.fetchone()

    conn.close()

    if row:
        return json.loads(row[0])

    return {
        "history": [],
        "facts": [],
        "fixes": [],
        "questions": [],
        "confidence": 0.0
    }


def save_case(case_id, data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    INSERT OR REPLACE INTO cases (id, created_at, data)
    VALUES (?, ?, ?)
    """, (
        case_id,
        datetime.utcnow().isoformat(),
        json.dumps(data)
    ))

    conn.commit()
    conn.close()
