"""Unit tests for the BookPipeline orchestration layer."""

from pathlib import Path
from unittest.mock import MagicMock

from src.pipeline.book_pipeline import BookPipeline
from src.scraper.book_scraper import BookScraper
from src.storage.sqlite_storage import SQLiteStorage


def test_pipeline_validation_separation(tmp_path: Path):
    """Verify that pipeline separates valid books from invalid ones without crashing."""
    storage = SQLiteStorage(db_path=tmp_path / "test.db")
    pipeline = BookPipeline(storage=storage)

    raw_records = [
        # Valid
        {
            "title": "Good Book 1",
            "price": 10.0,
            "rating": 3,
            "availability": "In stock",
            "detail_url": "http://books.toscrape.com/1",
        },
        # Invalid: empty title
        {
            "title": "",
            "price": 12.0,
            "rating": 2,
            "availability": "In stock",
            "detail_url": "http://books.toscrape.com/2",
        },
        # Invalid: negative price
        {
            "title": "Bad Price Book",
            "price": -4.0,
            "rating": 4,
            "availability": "In stock",
            "detail_url": "http://books.toscrape.com/3",
        },
        # Valid
        {
            "title": "Good Book 2",
            "price": 20.0,
            "rating": 5,
            "availability": "In stock",
            "detail_url": "http://books.toscrape.com/4",
        },
    ]

    valid_books, invalid_records = pipeline.validate_records(raw_records)

    assert len(valid_books) == 2
    assert len(invalid_records) == 2
    assert valid_books[0].title == "Good Book 1"
    assert valid_books[1].title == "Good Book 2"


def test_pipeline_end_to_end_mocked(tmp_path: Path):
    """Verify full pipeline execution using a mocked scraper and fresh SQLite DB."""
    db_file = tmp_path / "pipeline_run.db"
    storage = SQLiteStorage(db_path=db_file)

    mock_scraper = MagicMock(spec=BookScraper)
    mock_scraper.save_raw = False
    mock_scraper.raw_storage = None
    mock_scraper.scrape.return_value = [
        {
            "title": "Book Valid A",
            "price": 15.50,
            "rating": 4,
            "availability": "In stock",
            "detail_url": "http://books.toscrape.com/a",
        },
        {
            "title": "Book Invalid B",
            "price": 15.50,
            "rating": 99,  # rating out of range
            "availability": "In stock",
            "detail_url": "http://books.toscrape.com/b",
        },
        {
            "title": "Book Valid C",
            "price": 25.00,
            "rating": 5,
            "availability": "In stock",
            "detail_url": "http://books.toscrape.com/c",
        },
    ]

    pipeline = BookPipeline(scraper=mock_scraper, storage=storage)
    result = pipeline.run(start_url="http://books.toscrape.com/", max_pages=1)

    assert result.records_extracted == 3
    assert result.valid_records == 2
    assert result.invalid_records == 1
    assert result.records_persisted == 2
    assert storage.count_books() == 2

    # Scraper method called with appropriate arguments
    mock_scraper.scrape.assert_called_once_with(
        url="http://books.toscrape.com/", max_pages=1, run_id=None
    )
