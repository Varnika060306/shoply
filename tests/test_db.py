import re
import sqlite3
from datetime import date

import pytest
from werkzeug.security import check_password_hash

from database import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


def test_tables_exist():
    conn = db.get_db()
    names = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    conn.close()
    assert {"users", "expenses"} <= names


def test_init_db_idempotent():
    db.init_db()
    db.init_db()


def test_row_factory_and_foreign_keys_pragma():
    db.seed_db()
    conn = db.get_db()
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    row = conn.execute("SELECT email FROM users").fetchone()
    conn.close()
    assert row["email"] == "demo@spendly.com"


def test_foreign_key_enforced():
    conn = db.get_db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date) "
            "VALUES (?, ?, ?, ?)",
            (9999, 10.0, "Food", "2026-01-01"),
        )
    conn.close()


def test_unique_email():
    db.seed_db()
    conn = db.get_db()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Other", "demo@spendly.com", "x"),
        )
    conn.close()


def test_seed_idempotent():
    db.seed_db()
    db.seed_db()
    conn = db.get_db()
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    expense_count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()
    assert user_count == 1
    assert expense_count == 8


def test_seed_categories_dates_amounts():
    db.seed_db()
    conn = db.get_db()
    user_id = conn.execute("SELECT id FROM users").fetchone()["id"]
    rows = conn.execute("SELECT * FROM expenses").fetchall()
    conn.close()

    assert {row["category"] for row in rows} == set(db.CATEGORIES)
    month_prefix = date.today().strftime("%Y-%m")
    for row in rows:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["date"])
        assert row["date"].startswith(month_prefix)
        assert isinstance(row["amount"], float)
        assert row["user_id"] == user_id


def test_password_hashed():
    db.seed_db()
    conn = db.get_db()
    password_hash = conn.execute("SELECT password_hash FROM users").fetchone()[0]
    conn.close()
    assert password_hash != "demo123"
    assert check_password_hash(password_hash, "demo123")
    assert not check_password_hash(password_hash, "wrong")
