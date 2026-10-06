"""SQLite storage component for persisting and querying validated Book models."""

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from src.models.book import Book

logger = logging.getLogger(__name__)

CREATE_BOOKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    price REAL NOT NULL,
    rating INTEGER,
    availability TEXT NOT NULL,
    detail_url TEXT NOT NULL UNIQUE,
    scraped_at TEXT NOT NULL
);
"""

UPSERT_BOOK_SQL = """
INSERT INTO books (title, price, rating, availability, detail_url, scraped_at)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(detail_url) DO UPDATE SET
    title = excluded.title,
    price = excluded.price,
    rating = excluded.rating,
    availability = excluded.availability,
    scraped_at = excluded.scraped_at;
"""


class SQLiteStorage:
    """Manages SQLite database connections, schema setup, and Book record persistence."""

    def __init__(self, db_path: Path | str = "data/processed/books.db") -> None:
        """Initialize SQLiteStorage with database file path.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self._ensure_parent_dir()
        self.init_db()

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
        """Initialize the database schema (creates books table if not exists)."""
        with self.get_connection() as conn:
            conn.execute(CREATE_BOOKS_TABLE_SQL)
        logger.info("Initialized SQLite database schema at %s", self.db_path)

    def insert_book(self, book: Book) -> None:
        """Insert or upsert a single validated Book model.

        Args:
            book: Validated Book instance.
        """
        with self.get_connection() as conn:
            conn.execute(
                UPSERT_BOOK_SQL,
                (
                    book.title,
                    book.price,
                    book.rating,
                    book.availability,
                    book.detail_url,
                    book.scraped_at.isoformat(),
                ),
            )
        logger.debug("Persisted book: %s", book.title)

    def insert_books(self, books: list[Book]) -> int:
        """Insert or upsert multiple validated Book models in a single transaction.

        Args:
            books: List of validated Book instances.

        Returns:
            Number of books persisted.
        """
        if not books:
            return 0

        params = [
            (
                b.title,
                b.price,
                b.rating,
                b.availability,
                b.detail_url,
                b.scraped_at.isoformat(),
            )
            for b in books
        ]

        with self.get_connection() as conn:
            conn.executemany(UPSERT_BOOK_SQL, params)

        logger.info("Persisted %d books to %s", len(books), self.db_path)
        return len(books)

    def count_books(self) -> int:
        """Get the total count of books in the table.

        Returns:
            Integer total count.
        """
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM books;")
            count = cursor.fetchone()[0]
        return count

    def get_all_books(self) -> list[dict]:
        """Retrieve all books from the database ordered by id.

        Returns:
            List of dictionaries representing book records.
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, title, price, rating, availability, detail_url, scraped_at FROM books ORDER BY id ASC;"
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_book_by_url(self, detail_url: str) -> dict | None:
        """Retrieve a specific book by detail URL.

        Args:
            detail_url: Target detail URL.

        Returns:
            Dictionary record or None if not found.
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, title, price, rating, availability, detail_url, scraped_at FROM books WHERE detail_url = ?;",
                (detail_url,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
