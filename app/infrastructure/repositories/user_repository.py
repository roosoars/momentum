"""Repository for User persistence."""

import sqlite3
from datetime import datetime
from typing import List, Optional

from app.domain.models.user import User


class UserRepository:
    """Repository for managing User entities in SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialize_table()

    def _initialize_table(self) -> None:
        """Create users table if it doesn't exist and migrate schema if needed."""
        with sqlite3.connect(self.db_path) as conn:
            # Create table if it doesn't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    is_verified INTEGER DEFAULT 0,
                    verification_token TEXT,
                    verification_expires_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Migrate existing table: check and add missing columns
            cursor = conn.execute("PRAGMA table_info(users)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            # Add is_active if missing (for admin compatibility)
            if "is_active" not in existing_columns:
                conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")

            # Add is_verified if missing (for email verification)
            if "is_verified" not in existing_columns:
                conn.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")

            # Add verification_token if missing
            if "verification_token" not in existing_columns:
                conn.execute("ALTER TABLE users ADD COLUMN verification_token TEXT")

            # Add verification_expires_at if missing
            if "verification_expires_at" not in existing_columns:
                conn.execute("ALTER TABLE users ADD COLUMN verification_expires_at TEXT")

            # Create indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token)"
            )
            conn.commit()

    def create(
        self,
        email: str,
        password_hash: str,
        verification_token: Optional[str] = None,
        verification_expires_at: Optional[datetime] = None,
    ) -> User:
        """Create a new user."""
        now = datetime.utcnow().isoformat()
        verification_exp_str = (
            verification_expires_at.isoformat() if verification_expires_at else None
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (
                    email, password_hash, is_active, is_verified, verification_token,
                    verification_expires_at, created_at, updated_at
                )
                VALUES (?, ?, 1, 0, ?, ?, ?, ?)
                """,
                (
                    email,
                    password_hash,
                    verification_token,
                    verification_exp_str,
                    now,
                    now,
                ),
            )
            conn.commit()
            user_id = cursor.lastrowid

        return User(
            id=user_id,
            email=email,
            password_hash=password_hash,
            is_active=True,
            is_verified=False,
            verification_token=verification_token,
            verification_expires_at=verification_expires_at,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_user(row)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_user(row)

    def get_by_verification_token(self, token: str) -> Optional[User]:
        """Get user by verification token."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM users WHERE verification_token = ?", (token,)
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_user(row)

    def verify_email(self, user_id: int) -> None:
        """Mark user's email as verified."""
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE users
                SET is_verified = 1, verification_token = NULL,
                    verification_expires_at = NULL, updated_at = ?
                WHERE id = ?
                """,
                (now, user_id),
            )
            conn.commit()

    def update_verification_token(
        self,
        user_id: int,
        token: str,
        expires_at: datetime,
    ) -> None:
        """Update user's verification token."""
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE users
                SET verification_token = ?, verification_expires_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (token, expires_at.isoformat(), now, user_id),
            )
            conn.commit()

    def list_all(self) -> List[User]:
        """List all users."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users ORDER BY created_at DESC")
            rows = cursor.fetchall()

        return [self._row_to_user(row) for row in rows]

    def delete(self, user_id: int) -> None:
        """Delete a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

    def _row_to_user(self, row: sqlite3.Row) -> User:
        """Convert database row to User entity."""
        verification_exp = None
        if row["verification_expires_at"]:
            verification_exp = datetime.fromisoformat(row["verification_expires_at"])

        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            is_active=bool(row["is_active"]),
            is_verified=bool(row["is_verified"]),
            verification_token=row["verification_token"],
            verification_expires_at=verification_exp,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
