"""SQLite-хранилище: дедупликация объявлений и состояние приложения."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from models import Ad


class Store:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS seen_ads (
                key TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                price REAL,
                city TEXT,
                params_json TEXT,
                first_seen INTEGER NOT NULL,
                last_seen INTEGER NOT NULL,
                notified_at INTEGER
            );
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    # --- объявления (дедупликация) ---

    def is_new(self, key: str) -> bool:
        row = self.conn.execute(
            "SELECT key FROM seen_ads WHERE key = ?", (key,)
        ).fetchone()
        return row is None

    def mark_seen(self, ad: Ad, notified: bool = False) -> None:
        now = int(time.time())
        self.conn.execute(
            """
            INSERT INTO seen_ads
                (key, url, title, price, city, params_json, first_seen, last_seen, notified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                last_seen = excluded.last_seen,
                price = excluded.price,
                title = excluded.title,
                notified_at = CASE
                    WHEN excluded.notified_at IS NOT NULL THEN excluded.notified_at
                    ELSE seen_ads.notified_at
                END
            """,
            (
                ad.key,
                ad.url,
                ad.title,
                ad.price_byn,
                ad.city,
                json.dumps(ad.params, ensure_ascii=False),
                now,
                now,
                now if notified else None,
            ),
        )
        self.conn.commit()

    # --- состояние приложения ---

    def set_state(self, key: str, value: str) -> None:
        self.conn.execute(
            """
            INSERT INTO app_state (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self.conn.commit()

    def get_state(self, key: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT value FROM app_state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None
