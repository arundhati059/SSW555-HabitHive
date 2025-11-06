# habits_repo.py
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, Boolean,
    DateTime, ForeignKey, select, text, Index
)

# -------------------------
# Engine
# -------------------------
def make_engine(database_url: str = "sqlite:///habits.db"):
    """Create and return a SQLAlchemy engine (SQLite by default)."""
    return create_engine(database_url, future=True)

# -------------------------
# Schema (module-level, shared)
# -------------------------
metadata = MetaData()

habits = Table(
    "habits", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", String, nullable=False, index=True),
    Column("name", String, nullable=False),
    Column("description", String),
    Column("frequency", String, nullable=False, server_default="daily"),  # daily/weekly
    Column("reminder", String),
    Column("is_archived", Boolean, nullable=False, server_default=text("0")),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)
Index("ix_habits_user_active", habits.c.user_id, habits.c.is_archived)

journal_entries = Table(
    "journal_entries", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", String, nullable=False, index=True),
    Column("habit_id", Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False),
    Column("text", String, nullable=False),
    Column("mood", String),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
)

users = Table(
    "users", metadata,
    Column("user_id", String, primary_key=True),
    Column("display_name", String),
    Column("email", String),
)

# -------------------------
# DB init
# -------------------------
def init_db(engine):
    """Create tables if they do not exist."""
    metadata.create_all(engine)

# -------------------------
# Helpers
# -------------------------
def _row_to_dict(row) -> Dict[str, Any]:
    # SQLAlchemy 2.x: row is Row; use _mapping
    return dict(row._mapping)

# -------------------------
# Habits
# -------------------------
def add_habit(engine, habit_data: Dict[str, Any]) -> bool:
    """
    Add a new habit. habit_data must include:
    - user_id (str), name (str)
    Optional: description, frequency, reminder
    """
    required = ("user_id", "name")
    for key in required:
        if not habit_data.get(key):
            raise ValueError(f"'{key}' is required")

    payload = {
        "user_id": habit_data["user_id"],
        "name": habit_data["name"].strip(),
        "description": (habit_data.get("description") or "").strip(),
        "frequency": (habit_data.get("frequency") or "daily").strip(),
        "reminder": (habit_data.get("reminder") or "").strip(),
        "is_archived": bool(habit_data.get("is_archived", False)),
        "created_at": habit_data.get("created_at") or datetime.utcnow(),
    }

    try:
        with engine.begin() as conn:  # ensures commit
            conn.execute(habits.insert().values(**payload))
        return True
    except Exception as e:
        print(f"Error adding habit: {e}")
        return False

def list_active(engine, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List non-archived habits. If user_id is provided, filter by it.
    """
    stmt = select(habits).where(habits.c.is_archived == False)  # noqa: E712
    if user_id:
        stmt = stmt.where(habits.c.user_id == user_id)

    try:
        with engine.connect() as conn:
            rows = conn.execute(stmt).all()
            return [_row_to_dict(r) for r in rows]
    except Exception as e:
        print(f"Error listing active habits: {e}")
        return []

# -------------------------
# Journal
# -------------------------
def add_journal_entry(
    engine,
    entry: Dict[str, Any],  # expects user_id, habit_id, text; optional mood
) -> bool:
    required = ("user_id", "habit_id", "text")
    for key in required:
        if not entry.get(key):
            raise ValueError(f"'{key}' is required")

    payload = {
        "user_id": entry["user_id"],
        "habit_id": entry["habit_id"],
        "text": entry["text"].strip(),
        "mood": (entry.get("mood") or "").strip(),
        "created_at": entry.get("created_at") or datetime.utcnow(),
    }

    try:
        with engine.begin() as conn:
            conn.execute(journal_entries.insert().values(**payload))
        return True
    except Exception as e:
        print(f"Error adding journal entry: {e}")
        return False

# -------------------------
# Profile (read-only)
# -------------------------
def get_profile(engine, user_id: str) -> Dict[str, Any]:
    """
    Return a lightweight profile dict:
      { user_id, display_name, email, active_habits, journal_entries }
    """
    try:
        with engine.connect() as conn:
            # user info (optional)
            urow = conn.execute(
                select(users).where(users.c.user_id == user_id)
            ).first()
            u = _row_to_dict(urow) if urow else {"user_id": user_id}

            # counts
            active_count = conn.execute(
                select(habits.c.id).where(
                    habits.c.user_id == user_id,
                    habits.c.is_archived == False  # noqa: E712
                )
            ).rowcount  # rowcount is fine on SQLite SELECT here

            # More portable: count via subquery
            if active_count is None:
                active_count = len(conn.execute(
                    select(habits.c.id).where(
                        habits.c.user_id == user_id,
                        habits.c.is_archived == False  # noqa: E712
                    )
                ).all())

            journal_count = len(conn.execute(
                select(journal_entries.c.id).where(
                    journal_entries.c.user_id == user_id
                )
            ).all())

        return {
            "user_id": user_id,
            "display_name": u.get("display_name") or "User",
            "email": u.get("email", ""),
            "active_habits": active_count,
            "journal_entries": journal_count,
        }
    except Exception as e:
        print(f"Error building profile: {e}")
        return {
            "user_id": user_id,
            "display_name": "User",
            "email": "",
            "active_habits": 0,
            "journal_entries": 0,
        }
