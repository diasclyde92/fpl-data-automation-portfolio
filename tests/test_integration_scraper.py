"""Integration tests hitting the live public test website.

These tests make external HTTP requests and are separated from unit tests.
Marked with @pytest.mark.integration so they can be run explicitly or omitted.
"""

import pytest

from src.scraper.book_scraper import BookScraper


@pytest.mark.integration
def test_live_scrape_books_toscrape():
    """Verify live extraction against the public books.toscrape.com home page."""
    scraper = BookScraper()
    records = scraper.scrape(BookScraper.DEFAULT_BASE_URL)

    # books.toscrape.com displays 20 items per page
    assert len(records) == 20

    first_item = records[0]
    assert isinstance(first_item["title"], str)
    assert len(first_item["title"]) > 0
    assert isinstance(first_item["price"], float)
    assert first_item["price"] > 0
    assert isinstance(first_item["rating"], int)
    assert 1 <= first_item["rating"] <= 5
    assert first_item["detail_url"].startswith("http://books.toscrape.com/")
