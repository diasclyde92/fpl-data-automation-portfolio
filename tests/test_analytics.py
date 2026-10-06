"""Unit tests for the BookAnalytics layer."""

from pathlib import Path

import pandas as pd
import pytest

from src.analytics.book_analytics import BookAnalytics
from src.models.book import Book
from src.storage.sqlite_storage import SQLiteStorage


@pytest.fixture
def empty_storage(tmp_path: Path) -> SQLiteStorage:
    """Fixture providing a SQLiteStorage with zero records."""
    return SQLiteStorage(db_path=tmp_path / "empty.db")


@pytest.fixture
def sample_storage(tmp_path: Path) -> SQLiteStorage:
    """Fixture providing a populated SQLiteStorage with known test data."""
    storage = SQLiteStorage(db_path=tmp_path / "sample.db")
    books = [
        Book(
            title="Book Alpha",
            price=10.00,
            rating=1,
            availability="In stock",
            detail_url="http://books.toscrape.com/alpha",
        ),
        Book(
            title="Book Beta",
            price=20.00,
            rating=3,
            availability="In stock",
            detail_url="http://books.toscrape.com/beta",
        ),
        Book(
            title="Book Gamma",
            price=30.00,
            rating=5,
            availability="In stock",
            detail_url="http://books.toscrape.com/gamma",
        ),
        Book(
            title="Book Delta",
            price=40.00,
            rating=3,
            availability="Out of stock",
            detail_url="http://books.toscrape.com/delta",
        ),
        Book(
            title="Book Epsilon",
            price=50.00,
            rating=None,  # unrated
            availability="In stock",
            detail_url="http://books.toscrape.com/epsilon",
        ),
    ]
    storage.insert_books(books)
    return storage


def test_empty_database_analytics(empty_storage: SQLiteStorage):
    """Verify that an empty database is handled gracefully with zeroed statistics."""
    analytics = BookAnalytics(storage=empty_storage)
    df = analytics.load_data()

    assert df.empty
    assert list(df.columns) == ["id", "title", "price", "rating", "availability", "detail_url", "scraped_at"]

    result = analytics.analyze()
    assert result.summary.total_books == 0
    assert result.summary.average_price is None
    assert result.summary.median_price is None
    assert result.summary.min_price is None
    assert result.summary.max_price is None
    assert result.summary.average_rating is None
    assert result.quality.is_empty is True
    assert result.rating_distribution == {}
    assert result.top_expensive == []
    assert result.bottom_expensive == []


def test_load_data_types_and_values(sample_storage: SQLiteStorage):
    """Verify that load_data returns typed columns and correct row counts."""
    analytics = BookAnalytics(storage=sample_storage)
    df = analytics.load_data()

    assert len(df) == 5
    assert pd.api.types.is_float_dtype(df["price"])
    assert pd.api.types.is_integer_dtype(df["id"])
    assert pd.api.types.is_datetime64_any_dtype(df["scraped_at"])


def test_summary_statistics_calculations(sample_storage: SQLiteStorage):
    """Verify exact mathematical computations for summary statistics."""
    analytics = BookAnalytics(storage=sample_storage)
    df = analytics.load_data()
    summary = analytics.get_summary_statistics(df)

    # Prices: [10, 20, 30, 40, 50]
    # Sum = 150, Mean = 30, Median = 30, Min = 10, Max = 50
    assert summary.total_books == 5
    assert summary.min_price == 10.00
    assert summary.max_price == 50.00
    assert summary.average_price == 30.00
    assert summary.median_price == 30.00

    # Ratings: [1, 3, 5, 3] (one book has None)
    # Sum = 12, Count = 4, Mean = 3.0
    assert summary.average_rating == 3.00


def test_rating_distribution(sample_storage: SQLiteStorage):
    """Verify rating distribution frequency counts."""
    analytics = BookAnalytics(storage=sample_storage)
    df = analytics.load_data()
    distribution = analytics.get_rating_distribution(df)

    assert distribution == {1: 1, 3: 2, 5: 1}


def test_availability_distribution(sample_storage: SQLiteStorage):
    """Verify availability status frequency counts."""
    analytics = BookAnalytics(storage=sample_storage)
    df = analytics.load_data()
    availability = analytics.get_availability_distribution(df)

    assert availability == {"In stock": 4, "Out of stock": 1}


def test_top_and_bottom_expensive(sample_storage: SQLiteStorage):
    """Verify rankings for most and least expensive books."""
    analytics = BookAnalytics(storage=sample_storage)
    df = analytics.load_data()

    top_3 = analytics.get_top_expensive(df, n=3)
    assert len(top_3) == 3
    assert top_3[0]["title"] == "Book Epsilon"
    assert top_3[0]["price"] == 50.00
    assert top_3[1]["title"] == "Book Delta"
    assert top_3[1]["price"] == 40.00
    assert top_3[2]["title"] == "Book Gamma"
    assert top_3[2]["price"] == 30.00

    bottom_2 = analytics.get_bottom_expensive(df, n=2)
    assert len(bottom_2) == 2
    assert bottom_2[0]["title"] == "Book Alpha"
    assert bottom_2[0]["price"] == 10.00
    assert bottom_2[1]["title"] == "Book Beta"
    assert bottom_2[1]["price"] == 20.00


def test_top_rated(sample_storage: SQLiteStorage):
    """Verify top rated books ordering."""
    analytics = BookAnalytics(storage=sample_storage)
    df = analytics.load_data()
    top_rated = analytics.get_top_rated(df, n=3)

    assert len(top_rated) == 3
    # 5 stars
    assert top_rated[0]["title"] == "Book Gamma"
    assert top_rated[0]["rating"] == 5
    # 3 stars, higher price first (Delta: 40 vs Beta: 20)
    assert top_rated[1]["title"] == "Book Delta"
    assert top_rated[1]["rating"] == 3


def test_data_quality_report(sample_storage: SQLiteStorage):
    """Verify data quality reporting detects missing values and non-duplicates."""
    analytics = BookAnalytics(storage=sample_storage)
    df = analytics.load_data()
    quality = analytics.get_quality_report(df)

    assert quality.total_records == 5
    assert quality.missing_ratings == 1  # Book Epsilon has None
    assert quality.missing_prices == 0
    assert quality.missing_availability == 0
    assert quality.duplicate_urls == 0
    assert quality.is_empty is False


def test_analytics_result_to_dict(sample_storage: SQLiteStorage):
    """Verify full AnalyticsResult serialization to dictionary."""
    analytics = BookAnalytics(storage=sample_storage)
    result = analytics.analyze()
    result_dict = result.to_dict()

    assert isinstance(result_dict, dict)
    assert "summary" in result_dict
    assert "quality" in result_dict
    assert "rating_distribution" in result_dict
    assert "top_expensive" in result_dict
    assert result_dict["summary"]["total_books"] == 5
