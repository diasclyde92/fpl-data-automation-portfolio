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

CREATE_FPL_RUNS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fpl_runs (
    run_id TEXT PRIMARY KEY,
    scraped_at TEXT NOT NULL,
    source TEXT NOT NULL,
    records_extracted INTEGER NOT NULL DEFAULT 0,
    records_valid INTEGER NOT NULL DEFAULT 0,
    records_invalid INTEGER NOT NULL DEFAULT 0,
    records_persisted INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'started',
    duration_seconds REAL,
    error_message TEXT
);
"""

CREATE_FPL_SNAPSHOTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS fpl_player_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
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
    scraped_at TEXT NOT NULL,
    UNIQUE(run_id, player_id),
    FOREIGN KEY(run_id) REFERENCES fpl_runs(run_id)
);
"""

CREATE_FPL_SNAPSHOTS_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_snapshots_run_id ON fpl_player_snapshots(run_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_player_id ON fpl_player_snapshots(player_id);
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

INSERT_FPL_SNAPSHOT_SQL = """
INSERT OR IGNORE INTO fpl_player_snapshots (
    run_id, player_id, first_name, second_name, web_name, team, position,
    price, total_points, event_points, selected_by_percent,
    goals, assists, clean_sheets, minutes, bonus, form, status, scraped_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

INSERT_FPL_RUN_SQL = """
INSERT INTO fpl_runs (
    run_id, scraped_at, source, records_extracted, records_valid,
    records_invalid, records_persisted, status, duration_seconds, error_message
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

UPDATE_FPL_RUN_SQL = """
UPDATE fpl_runs SET
    records_extracted = ?,
    records_valid = ?,
    records_invalid = ?,
    records_persisted = ?,
    status = ?,
    duration_seconds = ?,
    error_message = ?
WHERE run_id = ?;
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
        """Initialize schema (creates fpl_players, fpl_runs, fpl_player_snapshots if not exist)."""
        with self.get_connection() as conn:
            conn.execute(CREATE_FPL_PLAYERS_TABLE_SQL)
            conn.execute(CREATE_FPL_RUNS_TABLE_SQL)
            conn.execute(CREATE_FPL_SNAPSHOTS_TABLE_SQL)
            conn.executescript(CREATE_FPL_SNAPSHOTS_INDEXES_SQL)
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

    # -----------------------------------------------------------------------
    # Historical Runs & Snapshots Management
    # -----------------------------------------------------------------------

    def create_run(
        self,
        run_id: str,
        source: str,
        scraped_at: str | None = None,
    ) -> None:
        """Record the initiation of a new pipeline run.

        Args:
            run_id: Unique run identifier.
            source: Source URL or endpoint description.
            scraped_at: ISO formatted UTC timestamp.
        """
        from datetime import datetime, timezone
        ts = scraped_at or datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                INSERT_FPL_RUN_SQL,
                (run_id, ts, source, 0, 0, 0, 0, "started", None, None),
            )
        logger.info("Created pipeline run record: %s", run_id)

    def complete_run(
        self,
        run_id: str,
        records_extracted: int,
        records_valid: int,
        records_invalid: int,
        records_persisted: int,
        duration_seconds: float | None = None,
        status: str = "completed",
    ) -> None:
        """Mark a pipeline run as completed with metrics.

        Args:
            run_id: Unique run identifier.
            records_extracted: Extracted records count.
            records_valid: Validated records count.
            records_invalid: Validation failures count.
            records_persisted: Records persisted count.
            duration_seconds: Execution duration in seconds.
            status: Final status string ('completed' or 'completed_with_errors').
        """
        with self.get_connection() as conn:
            conn.execute(
                UPDATE_FPL_RUN_SQL,
                (
                    records_extracted,
                    records_valid,
                    records_invalid,
                    records_persisted,
                    status,
                    duration_seconds,
                    None,
                    run_id,
                ),
            )
        logger.info("Completed pipeline run: %s with status=%s", run_id, status)

    def fail_run(
        self,
        run_id: str,
        error_message: str,
        records_extracted: int = 0,
        records_valid: int = 0,
        records_invalid: int = 0,
        duration_seconds: float | None = None,
    ) -> None:
        """Mark a pipeline run as failed.

        Args:
            run_id: Unique run identifier.
            error_message: Failure explanation or exception message.
            records_extracted: Extracted records count if known.
            records_valid: Validated records count if known.
            records_invalid: Validation failures count if known.
            duration_seconds: Execution duration before failure.
        """
        with self.get_connection() as conn:
            conn.execute(
                UPDATE_FPL_RUN_SQL,
                (
                    records_extracted,
                    records_valid,
                    records_invalid,
                    0,
                    "failed",
                    duration_seconds,
                    error_message,
                    run_id,
                ),
            )
        logger.warning("Marked pipeline run %s as failed: %s", run_id, error_message)

    def save_snapshots(self, run_id: str, players: list[FPLPlayer]) -> int:
        """Persist immutable historical player snapshots for a specific run.

        Uses INSERT OR IGNORE on UNIQUE(run_id, player_id) to guarantee idempotency.

        Args:
            run_id: Unique run identifier.
            players: List of validated FPLPlayer instances.

        Returns:
            Number of snapshot rows saved.
        """
        if not players:
            return 0

        params = [
            (
                run_id,
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
            cursor = conn.cursor()
            cursor.executemany(INSERT_FPL_SNAPSHOT_SQL, params)
            count = cursor.rowcount

        logger.info("Persisted %d historical player snapshots for run %s", len(players), run_id)
        return count if count >= 0 else len(players)

    def save_current_and_snapshots(
        self,
        run_id: str,
        players: list[FPLPlayer],
    ) -> int:
        """Atomically persist current-state players and historical snapshots in a single transaction.

        Args:
            run_id: Unique run identifier.
            players: List of validated FPLPlayer instances.

        Returns:
            Number of players persisted.
        """
        if not players:
            return 0

        current_params = [
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

        snapshot_params = [
            (
                run_id,
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
            conn.executemany(UPSERT_FPL_PLAYER_SQL, current_params)
            conn.executemany(INSERT_FPL_SNAPSHOT_SQL, snapshot_params)

        logger.info("Atomically saved %d current players and snapshots for run %s", len(players), run_id)
        return len(players)

    def count_runs(self) -> int:
        """Get total count of runs recorded."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM fpl_runs;")
            return cursor.fetchone()[0]

    def count_snapshots(self, run_id: str | None = None) -> int:
        """Get total count of historical snapshots (optionally for a specific run)."""
        with self.get_connection() as conn:
            if run_id:
                cursor = conn.execute("SELECT COUNT(*) FROM fpl_player_snapshots WHERE run_id = ?;", (run_id,))
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM fpl_player_snapshots;")
            return cursor.fetchone()[0]

    def get_latest_run(self) -> dict[str, Any] | None:
        """Retrieve most recent pipeline run record."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM fpl_runs ORDER BY scraped_at DESC LIMIT 1;")
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_run_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve run history ordered from newest to oldest."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM fpl_runs ORDER BY scraped_at DESC LIMIT ?;", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_snapshot(self, run_id: str) -> list[dict[str, Any]]:
        """Retrieve all player snapshot records for a specific run."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM fpl_player_snapshots WHERE run_id = ? ORDER BY total_points DESC, player_id ASC;",
                (run_id,),
            )
            return [dict(r) for r in cursor.fetchall()]

    def get_player_history(self, player_id: int) -> list[dict[str, Any]]:
        """Retrieve historical snapshot progression for an individual player across all runs.

        Args:
            player_id: Integer player ID.

        Returns:
            List of player snapshots ordered chronologically (scraped_at ASC).
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM fpl_player_snapshots WHERE player_id = ? ORDER BY scraped_at ASC;",
                (player_id,),
            )
            return [dict(r) for r in cursor.fetchall()]
