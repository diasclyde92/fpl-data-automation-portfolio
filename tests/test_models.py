"""Unit tests for the Book Pydantic data model."""

import pytest
from pydantic import ValidationError

from src.models.book import Book


def test_book_valid():
    """Verify that a valid book record passes validation cleanly."""
    book = Book(
        title="A Light in the Attic",
        price=51.77,
        rating=3,
        availability="In stock",
        detail_url="http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
    )
    assert book.title == "A Light in the Attic"
    assert book.price == 51.77
    assert book.rating == 3
    assert book.availability == "In stock"
    assert book.detail_url == "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    assert book.scraped_at is not None


def test_book_rating_none_is_allowed():
    """Verify rating=None is valid for unrated books."""
    book = Book(
        title="Unrated Book",
        price=12.50,
        rating=None,
        availability="In stock",
        detail_url="http://books.toscrape.com/catalogue/unrated/index.html",
    )
    assert book.rating is None


def test_book_missing_title_raises_error():
    """Verify missing title triggers a validation error."""
    with pytest.raises(ValidationError):
        Book(
            title="",
            price=10.0,
            availability="In stock",
            detail_url="http://example.com/b1",
        )


def test_book_whitespace_title_raises_error():
    """Verify purely whitespace title triggers a validation error."""
    with pytest.raises(ValidationError):
        Book(
            title="   ",
            price=10.0,
            availability="In stock",
            detail_url="http://example.com/b1",
        )


def test_book_negative_price_raises_error():
    """Verify negative price triggers a validation error."""
    with pytest.raises(ValidationError):
        Book(
            title="Free or Broken Book",
            price=-5.0,
            availability="In stock",
            detail_url="http://example.com/b1",
        )


def test_book_invalid_rating_scale_raises_error():
    """Verify rating outside 1..5 triggers a validation error."""
    with pytest.raises(ValidationError):
        Book(
            title="Overrated Book",
            price=10.0,
            rating=6,
            availability="In stock",
            detail_url="http://example.com/b1",
        )

    with pytest.raises(ValidationError):
        Book(
            title="Underrated Book",
            price=10.0,
            rating=0,
            availability="In stock",
            detail_url="http://example.com/b1",
        )


def test_book_invalid_detail_url_raises_error():
    """Verify invalid/relative URLs trigger a validation error."""
    with pytest.raises(ValidationError):
        Book(
            title="Book with Bad URL",
            price=10.0,
            availability="In stock",
            detail_url="not-a-valid-url",
        )

    with pytest.raises(ValidationError):
        Book(
            title="Book with FTP URL",
            price=10.0,
            availability="In stock",
            detail_url="ftp://example.com/book",
        )


def test_book_normalization_behavior():
    """Verify that title and availability strip extra whitespace."""
    book = Book(
        title="   Padded Title   ",
        price=15.0,
        availability="   In   stock   now   ",
        detail_url="http://example.com/book",
    )
    assert book.title == "Padded Title"
    assert book.availability == "In stock now"
