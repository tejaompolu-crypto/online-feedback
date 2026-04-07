import sqlite3
import os
import threading
import config

_thread_local = threading.local()


def get_db():
    """Get thread-local database connection with Row factory."""
    if not hasattr(_thread_local, "connection") or _thread_local.connection is None:
        conn = sqlite3.connect(
            config.DATABASE_PATH,
            timeout=5,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _thread_local.connection = conn
    return _thread_local.connection


def close_db(exception=None):
    """Close thread-local database connection."""
    conn = getattr(_thread_local, "connection", None)
    if conn:
        conn.close()
        _thread_local.connection = None


def init_db():
    """Create tables and seed default config if not exists."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            feedback_text TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            reply TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.execute(
        "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
        ("admin_secret_key", config.ADMIN_SECRET_KEY),
    )
    conn.commit()


def set_config(key, value):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()


def get_config(key):
    conn = get_db()
    result = conn.execute(
        "SELECT value FROM config WHERE key = ?", (key,)
    ).fetchone()
    if result:
        return result["value"]
    if key == "admin_secret_key":
        set_config(key, config.ADMIN_SECRET_KEY)
        return config.ADMIN_SECRET_KEY
    return None


def add_feedback(name, email, rating, feedback_text, category):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO feedback (name, email, rating, feedback_text, category) VALUES (?, ?, ?, ?, ?)",
        (name, email, rating, feedback_text, category),
    )
    conn.commit()
    return cursor.lastrowid


def get_feedback_by_id(feedback_id):
    conn = get_db()
    return conn.execute(
        "SELECT * FROM feedback WHERE id = ?", (feedback_id,)
    ).fetchone()


def get_all_feedback(
    sort_by="created_at",
    sort_order="DESC",
    category=None,
    rating=None,
    search=None,
    page=1,
    per_page=20,
):
    conn = get_db()

    sort_whitelist = ["id", "name", "email", "rating", "category", "created_at"]
    if sort_by not in sort_whitelist:
        sort_by = "created_at"
    if sort_order.upper() not in ("ASC", "DESC"):
        sort_order = "DESC"

    where_clauses = ["1=1"]
    params = []

    if category and category != "all":
        where_clauses.append("category = ?")
        params.append(category)

    if rating and rating != "all":
        where_clauses.append("rating = ?")
        params.append(int(rating))

    if search:
        like = f"%{search}%"
        where_clauses.append(
            "(name LIKE ? OR email LIKE ? OR feedback_text LIKE ?)"
        )
        params.extend([like, like, like])

    where_sql = " AND ".join(where_clauses)
    offset = (page - 1) * per_page

    total = conn.execute(
        f"SELECT COUNT(*) FROM feedback WHERE {where_sql}", params
    ).fetchone()[0]

    rows = conn.execute(
        f"SELECT * FROM feedback WHERE {where_sql} ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()

    return rows, total


def delete_feedback(feedback_id):
    conn = get_db()
    cursor = conn.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
    conn.commit()
    return cursor.rowcount > 0


def update_feedback_reply(feedback_id, reply_text):
    conn = get_db()
    conn.execute(
        "UPDATE feedback SET reply = ? WHERE id = ?", (reply_text, feedback_id)
    )
    conn.commit()


def get_all_for_export():
    conn = get_db()
    return conn.execute("SELECT * FROM feedback ORDER BY created_at").fetchall()


def count_all():
    conn = get_db()
    return conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
