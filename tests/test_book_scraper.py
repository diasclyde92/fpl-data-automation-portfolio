"""Unit tests for the BookScraper implementation using mocked HTML fixtures."""

from unittest.mock import MagicMock

import pytest
import requests
from bs4 import BeautifulSoup

from src.scraper.book_scraper import BookScraper
from src.scraper.http_client import HTTPClient

SAMPLE_BOOKS_HTML = """
<!DOCTYPE html>
<html>
<body>
    <ol class="row">
        <li class="col-xs-6 col-sm-4 col-md-3 col-lg-3">
            <article class="product_pod">
                <div class="image_container">
                    <a href="catalogue/a-light-in-the-attic_1000/index.html">
                        <img src="media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg" alt="A Light in the Attic" class="thumbnail">
                    </a>
                </div>
                <p class="star-rating Three">
                    <i class="icon-star"></i>
                </p>
                <h3>
                    <a href="catalogue/a-light-in-the-attic_1000/index.html" title="A Light in the Attic">A Light in the ...</a>
                </h3>
                <div class="product_price">
                    <p class="price_color">£51.77</p>
                    <p class="instock availability">
                        <i class="icon-ok"></i>
                        In stock
                    </p>
                </div>
            </article>
        </li>
        <li class="col-xs-6 col-sm-4 col-md-3 col-lg-3">
            <article class="product_pod">
                <p class="star-rating Five">
                    <i class="icon-star"></i>
                </p>
                <h3>
                    <a href="catalogue/tipping-the-velvet_999/index.html" title="Tipping the Velvet">Tipping the Velvet</a>
                </h3>
                <div class="product_price">
                    <p class="price_color">£53.74</p>
                    <p class="instock availability">
                        <i class="icon-ok"></i>
                        In stock
                    </p>
                </div>
            </article>
        </li>
    </ol>
</body>
</html>
"""


@pytest.fixture
def book_scraper() -> BookScraper:
    """Fixture providing a BookScraper instance."""
    return BookScraper(base_url="http://books.toscrape.com/")


def test_extract_multiple_records(book_scraper: BookScraper):
    """Verify that multiple records are extracted with normalized values."""
    soup = BeautifulSoup(SAMPLE_BOOKS_HTML, "html.parser")
    records = book_scraper.extract(soup)

    assert len(records) == 2

    # Record 1
    assert records[0]["title"] == "A Light in the Attic"
    assert records[0]["price"] == 51.77
    assert records[0]["rating"] == 3
    assert records[0]["availability"] == "In stock"
    assert (
        records[0]["detail_url"]
        == "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    )

    # Record 2
    assert records[1]["title"] == "Tipping the Velvet"
    assert records[1]["price"] == 53.74
    assert records[1]["rating"] == 5
    assert records[1]["availability"] == "In stock"
    assert (
        records[1]["detail_url"]
        == "http://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html"
    )


def test_extract_missing_optional_fields(book_scraper: BookScraper):
    """Verify that missing price, rating, or availability doesn't crash the scraper."""
    partial_html = """
    <article class="product_pod">
        <h3>
            <a href="catalogue/incomplete-book_1/index.html" title="Incomplete Book">Incomplete Book</a>
        </h3>
        <!-- Missing star-rating, price_color, availability -->
    </article>
    """
    soup = BeautifulSoup(partial_html, "html.parser")
    records = book_scraper.extract(soup)

    assert len(records) == 1
    assert records[0]["title"] == "Incomplete Book"
    assert records[0]["price"] is None
    assert records[0]["rating"] is None
    assert records[0]["availability"] == "Unknown"
    assert records[0]["detail_url"] == "http://books.toscrape.com/catalogue/incomplete-book_1/index.html"


def test_extract_malformed_pod_skipped(book_scraper: BookScraper):
    """Verify that pods without any title or anchor tag are safely skipped."""
    malformed_html = """
    <div>
        <article class="product_pod">
            <!-- No h3 or anchor -->
            <p class="star-rating One"></p>
        </article>
        <article class="product_pod">
            <h3><a href="book-1" title="Valid Book">Valid</a></h3>
        </article>
    </div>
    """
    soup = BeautifulSoup(malformed_html, "html.parser")
    records = book_scraper.extract(soup)

    assert len(records) == 1
    assert records[0]["title"] == "Valid Book"


def test_scrape_full_workflow_mocked(book_scraper: BookScraper):
    """Verify the full scrape workflow with a mocked HTTP response."""
    mock_client = MagicMock(spec=HTTPClient)
    mock_response = MagicMock(spec=requests.Response)
    mock_response.text = SAMPLE_BOOKS_HTML
    mock_client.get.return_value = mock_response

    book_scraper.client = mock_client
    records = book_scraper.scrape("http://books.toscrape.com/")

    assert len(records) == 2
    mock_client.get.assert_called_once_with("http://books.toscrape.com/")
