"""SQLite storage component for persisting and querying validated FPL Player models."""

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from src.models.fpl_player import FPLPlayer

logger = logging.getLogger(__name__)

CREATE_FPL_PLAYERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fpl_players (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    second_name TEXT NOT NULL,
    web_name TEXT NOT NULL,
    team TEXT NOT NULL,
    position TEXT NOT NULL,
    price REAL NOT NULL,
    total_points INTEGER NOT NULL,
    event_points INTEGER NOT NULL,
    selected_by_percent REAL NOT NULL,
    goals INTEGER NOT NULL,
    assists INTEGER NOT NULL,
    clean_sheets INTEGER NOT NULL,
    minutes INTEGER NOT NULL,
    bonus INTEGER NOT NULL,
    form REAL NOT NULL,
    status TEXT NOT NULL,
    scraped_at TEXT NOT NULL
);
"""

UPSERT_FPL_PLAYER_SQL = """
INSERT INTO fpl_players (
    id, first_name, second_name, web_name, team, position,
    price, total_points, event_points, selected_by_percent,
    goals, assists, clean_sheets, minutes, bonus, form, status, scraped_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    first_name = excluded.first_name,
    second_name = excluded.second_name,
    web_name = excluded.web_name,
    team = excluded.team,
    position = excluded.position,
    price = excluded.price,
    total_points = excluded.total_points,
    event_points = excluded.event_points,
    selected_by_percent = excluded.selected_by_percent,
    goals = excluded.goals,
    assists = excluded.assists,
    clean_sheets = excluded.clean_sheets,
    minutes = excluded.minutes,
    bonus = excluded.bonus,
    form = excluded.form,
    status = excluded.status,
    scraped_at = excluded.scraped_at;
"""


class FPLStorage:
    """Manages SQLite database connections, schema setup, and FPL player persistence."""

    def __init__(self, db_path: Path | str = "data/processed/fpl.db") -> None:
        """Initialize FPLStorage with database path.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self._ensure_parent_dir()
        self.init_db()

    def _ensure_parent_dir() -> None:
        pass

    def _ensure_parent_dir(self) -> None:
        """Ensure parent directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager providing a SQLite connection with row factory and auto commit/rollback."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize schema (creates fpl_players table if not exists)."""
        with self.get_connection() as conn:
            conn.execute(CREATE_FPL_PLAYERS_TABLE_SQL)
        logger.info("Initialized FPL SQLite schema at %s", self.db_path)

    def insert_player(self, player: FPLPlayer) -> None:
        """Insert or upsert a single FPLPlayer record.

        Args:
            player: Validated FPLPlayer instance.
        """
        with self.get_connection() as conn:
            conn.execute(
                UPSERT_FPL_PLAYER_SQL,
                (
                    player.id,
                    player.first_name,
                    player.second_name,
                    player.web_name,
                    player.team,
                    player.position,
                    player.price,
                    player.total_points,
                    player.event_points,
                    player.selected_by_percent,
                    player.goals,
                    player.assists,
                    player.clean_sheets,
                    player.minutes,
                    player.bonus,
                    player.form,
                    player.status,
                    player.scraped_at.isoformat(),
                ),
            )
        logger.debug("Persisted FPL player: %s (#%d)", player.web_name, player.id)

    def insert_players(self, players: list[FPLPlayer]) -> int:
        """Insert or upsert multiple FPLPlayer records in a single transaction.

        Args:
            players: List of validated FPLPlayer instances.

        Returns:
            Number of players inserted/updated.
        """
        if not players:
            return 0

        params = [
            (
                p.id,
                p.first_name,
                p.second_name,
                p.web_name,
                p.team,
                p.position,
                p.price,
                p.total_points,
                p.event_points,
                p.selected_by_percent,
                p.goals,
                p.assists,
                p.clean_sheets,
                p.minutes,
                p.bonus,
                p.form,
                p.status,
                p.scraped_at.isoformat(),
            )
            for p in players
        ]

        with self.get_connection() as conn:
            conn.executemany(UPSERT_FPL_PLAYER_SQL, params)

        logger.info("Persisted %d FPL players to %s", len(players), self.db_path)
        return len(players)

    def count_players(self) -> int:
        """Get total count of player rows in the table.

        Returns:
            Integer total player count.
        """
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM fpl_players;")
            count = cursor.fetchone()[0]
        return count

    def get_all_players(self) -> list[dict[str, Any]]:
        """Retrieve all player records ordered by total points descending.

        Returns:
            List of dictionaries representing player records.
        """
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM fpl_players ORDER BY total_points DESC, id ASC;")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_player_by_id(self, player_id: int) -> dict[str, Any] | None:
        """Retrieve a specific player by FPL element ID.

        Args:
            player_id: Integer player ID.

        Returns:
            Player record dictionary or None if not found.
        """
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM fpl_players WHERE id = ?;", (player_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
