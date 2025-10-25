"""Repository for Subscription persistence."""

import sqlite3
from datetime import datetime
from typing import List, Optional

from app.domain.models.subscription import Subscription


class SubscriptionRepository:
    """Repository for managing Subscription entities in SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialize_table()

    def _initialize_table(self) -> None:
        """Create subscriptions table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    stripe_customer_id TEXT NOT NULL,
                    stripe_subscription_id TEXT UNIQUE NOT NULL,
                    stripe_price_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_period_start TEXT NOT NULL,
                    current_period_end TEXT NOT NULL,
                    cancel_at_period_end INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_subscription_id ON subscriptions(stripe_subscription_id)"
            )
            conn.commit()

    def create(
        self,
        user_id: int,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        stripe_price_id: str,
        status: str,
        current_period_start: datetime,
        current_period_end: datetime,
        cancel_at_period_end: bool = False,
    ) -> Subscription:
        """Create a new subscription."""
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO subscriptions (
                    user_id, stripe_customer_id, stripe_subscription_id,
                    stripe_price_id, status, current_period_start,
                    current_period_end, cancel_at_period_end, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    stripe_customer_id,
                    stripe_subscription_id,
                    stripe_price_id,
                    status,
                    current_period_start.isoformat(),
                    current_period_end.isoformat(),
                    int(cancel_at_period_end),
                    now,
                    now,
                ),
            )
            conn.commit()
            subscription_id = cursor.lastrowid

        return Subscription(
            id=subscription_id,
            user_id=user_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_price_id=stripe_price_id,
            status=status,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            cancel_at_period_end=cancel_at_period_end,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    def get_by_id(self, subscription_id: int) -> Optional[Subscription]:
        """Get subscription by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM subscriptions WHERE id = ?", (subscription_id,)
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_subscription(row)

    def get_by_user_id(self, user_id: int) -> Optional[Subscription]:
        """Get active subscription for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM subscriptions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_subscription(row)

    def get_by_stripe_subscription_id(
        self, stripe_subscription_id: str
    ) -> Optional[Subscription]:
        """Get subscription by Stripe subscription ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM subscriptions WHERE stripe_subscription_id = ?",
                (stripe_subscription_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_subscription(row)

    def update_status(
        self,
        stripe_subscription_id: str,
        status: str,
        current_period_start: datetime,
        current_period_end: datetime,
        cancel_at_period_end: bool = False,
    ) -> None:
        """Update subscription status and period."""
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE subscriptions
                SET status = ?, current_period_start = ?, current_period_end = ?,
                    cancel_at_period_end = ?, updated_at = ?
                WHERE stripe_subscription_id = ?
                """,
                (
                    status,
                    current_period_start.isoformat(),
                    current_period_end.isoformat(),
                    int(cancel_at_period_end),
                    now,
                    stripe_subscription_id,
                ),
            )
            conn.commit()

    def list_by_user_id(self, user_id: int) -> List[Subscription]:
        """List all subscriptions for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM subscriptions
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()

        return [self._row_to_subscription(row) for row in rows]

    def delete(self, subscription_id: int) -> None:
        """Delete a subscription."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
            conn.commit()

    def _row_to_subscription(self, row: sqlite3.Row) -> Subscription:
        """Convert database row to Subscription entity."""
        return Subscription(
            id=row["id"],
            user_id=row["user_id"],
            stripe_customer_id=row["stripe_customer_id"],
            stripe_subscription_id=row["stripe_subscription_id"],
            stripe_price_id=row["stripe_price_id"],
            status=row["status"],
            current_period_start=datetime.fromisoformat(row["current_period_start"]),
            current_period_end=datetime.fromisoformat(row["current_period_end"]),
            cancel_at_period_end=bool(row["cancel_at_period_end"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
