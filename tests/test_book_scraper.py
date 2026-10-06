"""Unit tests for the BookScraper implementation using mocked HTML fixtures."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from bs4 import BeautifulSoup

from src.scraper.book_scraper import BookScraper
from src.scraper.http_client import HTTPClient
from src.storage.raw_storage import RawStorage

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

PAGE_1_HTML = """
<!DOCTYPE html>
<html>
<body>
    <article class="product_pod">
        <h3><a href="catalogue/book-1.html" title="Book 1">Book 1</a></h3>
        <p class="price_color">£10.00</p>
    </article>
    <ul class="pager">
        <li class="next"><a href="catalogue/page-2.html">next</a></li>
    </ul>
</body>
</html>
"""

PAGE_2_HTML = """
<!DOCTYPE html>
<html>
<body>
    <article class="product_pod">
        <h3><a href="catalogue/book-2.html" title="Book 2">Book 2</a></h3>
        <p class="price_color">£20.00</p>
    </article>
    <ul class="pager">
        <li class="previous"><a href="page-1.html">previous</a></li>
    </ul>
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


# ---------------------------------------------------------------------------
# Pagination Tests
# ---------------------------------------------------------------------------

def test_pagination_single_page_no_next(book_scraper: BookScraper):
    """Verify scraping terminates cleanly when page has no next link."""
    mock_client = MagicMock(spec=HTTPClient)
    mock_response = MagicMock(spec=requests.Response)
    mock_response.text = SAMPLE_BOOKS_HTML
    mock_client.get.return_value = mock_response

    book_scraper.client = mock_client
    records = book_scraper.scrape("http://books.toscrape.com/", max_pages=5)

    assert len(records) == 2
    mock_client.get.assert_called_once_with("http://books.toscrape.com/")


def test_pagination_two_pages_traversal(book_scraper: BookScraper):
    """Verify two-page traversal, extracting items across pages and following next link."""
    mock_client = MagicMock(spec=HTTPClient)
    resp1 = MagicMock(spec=requests.Response, text=PAGE_1_HTML)
    resp2 = MagicMock(spec=requests.Response, text=PAGE_2_HTML)
    mock_client.get.side_effect = [resp1, resp2]

    book_scraper.client = mock_client
    records = book_scraper.scrape("http://books.toscrape.com/", max_pages=5)

    assert len(records) == 2
    assert records[0]["title"] == "Book 1"
    assert records[1]["title"] == "Book 2"
    assert mock_client.get.call_count == 2
    mock_client.get.assert_any_call("http://books.toscrape.com/")
    mock_client.get.assert_any_call("http://books.toscrape.com/catalogue/page-2.html")


def test_pagination_relative_url_normalization(book_scraper: BookScraper):
    """Verify next page relative URL is normalized correctly into an absolute URL."""
    soup = BeautifulSoup('<li class="next"><a href="page-3.html">next</a></li>', "html.parser")
    next_url = book_scraper.get_next_page_url(soup, "http://books.toscrape.com/catalogue/page-2.html")
    assert next_url == "http://books.toscrape.com/catalogue/page-3.html"


def test_pagination_max_page_limit(book_scraper: BookScraper):
    """Verify pagination stops once max_pages limit is reached even if next page exists."""
    mock_client = MagicMock(spec=HTTPClient)
    resp1 = MagicMock(spec=requests.Response, text=PAGE_1_HTML)
    mock_client.get.return_value = resp1

    book_scraper.client = mock_client
    # PAGE_1 has a next link, but max_pages=1 restricts it
    records = book_scraper.scrape("http://books.toscrape.com/", max_pages=1)

    assert len(records) == 1
    assert mock_client.get.call_count == 1


def test_pagination_missing_or_malformed_next_link(book_scraper: BookScraper):
    """Verify get_next_page_url returns None when next link is missing or malformed."""
    soup_empty = BeautifulSoup('<li class="next"></li>', "html.parser")
    assert book_scraper.get_next_page_url(soup_empty, "http://example.com") is None

    soup_no_href = BeautifulSoup('<li class="next"><a>next</a></li>', "html.parser")
    assert book_scraper.get_next_page_url(soup_no_href, "http://example.com") is None


def test_pagination_loop_protection(book_scraper: BookScraper):
    """Verify scraper detects cyclic pagination links and breaks immediately."""
    loop_html = """
    <article class="product_pod">
        <h3><a href="book.html" title="Book Loop">Book</a></h3>
    </article>
    <li class="next"><a href="http://books.toscrape.com/loop.html">next</a></li>
    """
    mock_client = MagicMock(spec=HTTPClient)
    mock_response = MagicMock(spec=requests.Response, text=loop_html)
    mock_client.get.return_value = mock_response

    book_scraper.client = mock_client
    # Page points to itself
    records = book_scraper.scrape("http://books.toscrape.com/loop.html", max_pages=10)

    # First fetch succeeds, next points to visited URL and breaks loop
    assert len(records) == 1
    assert mock_client.get.call_count == 1


# ---------------------------------------------------------------------------
# Scraper + Raw Storage Integration Test (Mocked)
# ---------------------------------------------------------------------------

def test_scrape_with_raw_storage(tmp_path: Path):
    """Verify that enabling save_raw saves HTML pages to the configured storage directory."""
    mock_client = MagicMock(spec=HTTPClient)
    resp1 = MagicMock(spec=requests.Response, text=PAGE_1_HTML)
    resp2 = MagicMock(spec=requests.Response, text=PAGE_2_HTML)
    mock_client.get.side_effect = [resp1, resp2]

    storage = RawStorage(base_dir=tmp_path)
    scraper = BookScraper(
        client=mock_client,
        save_raw=True,
        raw_storage=storage,
        max_pages=2,
    )

    records = scraper.scrape("http://books.toscrape.com/", run_id="test_run_123")

    assert len(records) == 2
    raw_files = list((tmp_path / "books" / "test_run_123").glob("*.html"))
    assert len(raw_files) == 2
    assert (tmp_path / "books" / "test_run_123" / "page_001.html").exists()
    assert (tmp_path / "books" / "test_run_123" / "page_002.html").exists()
