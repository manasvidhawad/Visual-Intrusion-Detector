import sqlite3
import json
import hashlib
import secrets
import numpy as np
import os
import threading

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "privacy_guard.db")

# Thread-local storage for connections
_local = threading.local()


def get_db():
    """Get a thread-local database connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA busy_timeout=5000")
    return _local.conn


def init_db():
    """Create all tables and insert default settings."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        encoding BLOB NOT NULL,
        avatar_base64 TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS web_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        person TEXT,
        action TEXT,
        duration REAL,
        severity TEXT DEFAULT 'info'
    )
    """)

    default_settings = [
        ("alert_timer", "7"),
        ("protection_mode", "blur"),
        ("sensitivity", "0.5"),
        ("camera_index", "0"),
        ("sound_alert", "true"),
        ("escalation_seconds", "10"),
    ]
    for key, val in default_settings:
        cursor.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val)
        )

    conn.commit()


# Password Hashing 


def _hash_password(password: str, salt: str) -> str:
    """SHA-256 with per-user salt. Simple but effective."""
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


# Web User Auth CRUD 


def create_web_user(username: str, email: str, password: str) -> dict:
    """Create a new application account. Returns user dict or raises."""
    conn = get_db()
    cursor = conn.cursor()
    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)
    try:
        cursor.execute(
            "INSERT INTO web_users (username, email, password_hash, salt) VALUES (?, ?, ?, ?)",
            (username, email, pw_hash, salt),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "username": username, "email": email}
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            raise ValueError("Username already exists")
        if "email" in str(e):
            raise ValueError("Email already exists")
        raise


def authenticate_web_user(username: str, password: str) -> dict | None:
    """Verify credentials. Returns user dict or None."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, password_hash, salt FROM web_users WHERE username = ?",
        (username,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    pw_hash = _hash_password(password, row["salt"])
    if pw_hash != row["password_hash"]:
        return None
    return {"id": row["id"], "username": row["username"], "email": row["email"]}


def get_web_user_count() -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM web_users")
    return cursor.fetchone()[0]


# User CRUD 

def add_user(name: str, encoding: np.ndarray, avatar_base64: str = None) -> int:
    conn = get_db()
    cursor = conn.cursor()
    encoding_blob = encoding.tobytes()
    cursor.execute(
        "INSERT INTO users (name, encoding, avatar_base64) VALUES (?, ?, ?)",
        (name, encoding_blob, avatar_base64),
    )
    user_id = cursor.lastrowid
    conn.commit()
    return user_id


def get_all_users() -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, avatar_base64, created_at FROM users")
    return [dict(row) for row in cursor.fetchall()]


def get_user_encodings() -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, encoding FROM users")
    data = []
    for row in cursor.fetchall():
        encoding = np.frombuffer(row["encoding"], dtype=np.float64)
        data.append({"id": row["id"], "name": row["name"], "encoding": encoding})
    return data


def delete_user(user_id: int) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    return deleted


# Settings

def get_settings() -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    return {row["key"]: row["value"] for row in cursor.fetchall()}


def update_settings(updates: dict):
    conn = get_db()
    cursor = conn.cursor()
    for key, value in updates.items():
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
    conn.commit()


# Logs 


def add_log(person: str, action: str, duration: float, severity: str = "info"):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO logs (person, action, duration, severity) VALUES (?, ?, ?, ?)",
        (person, action, duration, severity),
    )
    conn.commit()


def get_logs(limit: int = 200) -> list:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    return [dict(row) for row in cursor.fetchall()]


def clear_logs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM logs")
    conn.commit()


init_db()

