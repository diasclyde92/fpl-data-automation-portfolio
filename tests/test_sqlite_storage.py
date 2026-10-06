"""Unit tests for the SQLiteStorage component."""

from pathlib import Path

import pytest

from src.models.book import Book
from src.storage.sqlite_storage import SQLiteStorage


@pytest.fixture
def storage(tmp_path: Path) -> SQLiteStorage:
    """Fixture providing a fresh SQLiteStorage instance with a temporary file."""
    db_file = tmp_path / "test_books.db"
    return SQLiteStorage(db_path=db_file)


def test_sqlite_initialization(storage: SQLiteStorage):
    """Verify that the database file and books table are created upon initialization."""
    assert storage.db_path.exists()
    assert storage.count_books() == 0


def test_insert_and_retrieve_single_book(storage: SQLiteStorage):
    """Verify inserting one book and retrieving it by detail_url."""
    book = Book(
        title="Test Book",
        price=19.99,
        rating=4,
        availability="In stock",
        detail_url="http://books.toscrape.com/catalogue/test-book/index.html",
    )

    storage.insert_book(book)

    assert storage.count_books() == 1
    retrieved = storage.get_book_by_url(book.detail_url)
    assert retrieved is not None
    assert retrieved["title"] == "Test Book"
    assert retrieved["price"] == 19.99
    assert retrieved["rating"] == 4
    assert retrieved["availability"] == "In stock"
    assert retrieved["detail_url"] == book.detail_url


def test_insert_multiple_books_and_get_all(storage: SQLiteStorage):
    """Verify bulk insertion and retrieving all books."""
    books = [
        Book(
            title=f"Book #{i}",
            price=float(10 * i),
            rating=i,
            availability="In stock",
            detail_url=f"http://books.toscrape.com/catalogue/book-{i}/index.html",
        )
        for i in range(1, 4)
    ]

    persisted = storage.insert_books(books)
    assert persisted == 3
    assert storage.count_books() == 3

    all_books = storage.get_all_books()
    assert len(all_books) == 3
    assert all_books[0]["title"] == "Book #1"
    assert all_books[2]["title"] == "Book #3"


def test_duplicate_upsert_strategy(storage: SQLiteStorage):
    """Verify that re-inserting a book with identical detail_url updates the record rather than duplicating."""
    book_v1 = Book(
        title="Original Title",
        price=10.00,
        rating=2,
        availability="Out of stock",
        detail_url="http://books.toscrape.com/catalogue/unique-slug/index.html",
    )
    storage.insert_book(book_v1)
    assert storage.count_books() == 1

    # Book with identical URL but updated price and availability
    book_v2 = Book(
        title="Updated Title",
        price=15.00,
        rating=4,
        availability="In stock",
        detail_url="http://books.toscrape.com/catalogue/unique-slug/index.html",
    )
    storage.insert_book(book_v2)

    # Total rows must remain 1
    assert storage.count_books() == 1

    updated = storage.get_book_by_url("http://books.toscrape.com/catalogue/unique-slug/index.html")
    assert updated is not None
    assert updated["title"] == "Updated Title"
    assert updated["price"] == 15.00
    assert updated["rating"] == 4
    assert updated["availability"] == "In stock"


def test_persistence_across_connections(tmp_path: Path):
    """Verify data persists when opening a new SQLiteStorage instance on the same DB file."""
    db_file = tmp_path / "persistent_books.db"
    storage1 = SQLiteStorage(db_path=db_file)
    book = Book(
        title="Persistent Book",
        price=25.00,
        rating=5,
        availability="In stock",
        detail_url="http://books.toscrape.com/catalogue/persistent/index.html",
    )
    storage1.insert_book(book)

    # Reconnect with a second storage instance
    storage2 = SQLiteStorage(db_path=db_file)
    assert storage2.count_books() == 1
    row = storage2.get_book_by_url(book.detail_url)
    assert row is not None
    assert row["title"] == "Persistent Book"
