"""Unit tests for the scraping foundation package."""

from unittest.mock import MagicMock, patch

import pytest
import requests
from bs4 import BeautifulSoup

from src.scraper.base_scraper import BaseScraper
from src.scraper.exceptions import ParsingError, RequestError
from src.scraper.http_client import HTTPClient
from src.scraper.parser import parse_html


# ---------------------------------------------------------------------------
# HTTPClient Tests
# ---------------------------------------------------------------------------

def test_http_client_successful_get():
    """Verify that HTTPClient returns a valid response on HTTP 200."""
    client = HTTPClient()
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.text = "<html><body><h1>Hello World</h1></body></html>"
    mock_response.raise_for_status.return_value = None

    with patch.object(client.session, "get", return_value=mock_response) as mock_get:
        response = client.get("https://example.com/test")

        assert response.status_code == 200
        assert response.text == "<html><body><h1>Hello World</h1></body></html>"
        mock_get.assert_called_once_with("https://example.com/test", timeout=10.0)


def test_http_client_fatal_client_error():
    """Verify that non-transient 4xx errors raise RequestError without unnecessary retries."""
    client = HTTPClient(max_retries=3)
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.HTTPError(
        "404 Client Error", response=mock_response
    )

    with patch.object(client.session, "get", return_value=mock_response) as mock_get:
        with pytest.raises(RequestError) as exc_info:
            client.get("https://example.com/not-found")

        assert exc_info.value.status_code == 404
        assert mock_get.call_count == 1


def test_http_client_transient_retry_success():
    """Verify that transient 503 errors trigger backoff retry and succeed when service recovers."""
    client = HTTPClient(max_retries=2, backoff_factor=0.01)

    fail_response = MagicMock(spec=requests.Response)
    fail_response.status_code = 503

    ok_response = MagicMock(spec=requests.Response)
    ok_response.status_code = 200
    ok_response.text = "Success"
    ok_response.raise_for_status.return_value = None

    with patch.object(client.session, "get", side_effect=[fail_response, ok_response]) as mock_get:
        with patch("time.sleep") as mock_sleep:
            response = client.get("https://example.com/service")

            assert response.status_code == 200
            assert mock_get.call_count == 2
            mock_sleep.assert_called_once_with(0.01)


def test_http_client_timeout_exhaustion():
    """Verify that persistent timeouts exhaust retries and raise RequestError."""
    client = HTTPClient(max_retries=2, backoff_factor=0.01)

    with patch.object(client.session, "get", side_effect=requests.Timeout("Request timed out")) as mock_get:
        with patch("time.sleep"):
            with pytest.raises(RequestError) as exc_info:
                client.get("https://example.com/timeout")

            assert "exhausted retries" in str(exc_info.value) or "Request failed" in str(exc_info.value)
            assert mock_get.call_count == 3  # initial attempt + 2 retries


def test_http_client_connection_error_retry():
    """Verify that connection errors are retried up to max_retries."""
    client = HTTPClient(max_retries=1, backoff_factor=0.01)

    with patch.object(
        client.session, "get", side_effect=requests.ConnectionError("Connection refused")
    ) as mock_get:
        with patch("time.sleep"):
            with pytest.raises(RequestError):
                client.get("https://example.com/conn-error")

            assert mock_get.call_count == 2


# ---------------------------------------------------------------------------
# HTML Parser Tests
# ---------------------------------------------------------------------------

def test_parse_html_success():
    """Verify that parse_html returns a BeautifulSoup object and parses tags correctly."""
    html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <div class="player" data-id="1">
                <span class="name">Mohamed Salah</span>
                <span class="points">185</span>
            </div>
        </body>
    </html>
    """
    soup = parse_html(html)
    assert isinstance(soup, BeautifulSoup)
    assert soup.title.string == "Test Page"

    player = soup.find("div", class_="player")
    assert player is not None
    assert player.find("span", class_="name").get_text() == "Mohamed Salah"
    assert player.find("span", class_="points").get_text() == "185"


def test_parse_html_invalid_input():
    """Verify that non-string input raises a ParsingError."""
    with pytest.raises(ParsingError):
        parse_html(123)  # type: ignore


# ---------------------------------------------------------------------------
# BaseScraper Lifecycle Tests
# ---------------------------------------------------------------------------

class DummyProductScraper(BaseScraper):
    """Concrete dummy scraper for testing the base scraper lifecycle."""

    def extract(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        items = []
        for item in soup.find_all("li", class_="item"):
            items.append({"title": item.get_text(strip=True)})
        return items


def test_base_scraper_workflow():
    """Verify the full scrape workflow: fetch -> parse -> extract."""
    mock_client = MagicMock(spec=HTTPClient)
    mock_response = MagicMock(spec=requests.Response)
    mock_response.text = """
    <ul>
        <li class="item">Item 1</li>
        <li class="item">Item 2</li>
    </ul>
    """
    mock_client.get.return_value = mock_response

    scraper = DummyProductScraper(client=mock_client)
    data = scraper.scrape("https://example.com/items")

    assert data == [{"title": "Item 1"}, {"title": "Item 2"}]
    mock_client.get.assert_called_once_with("https://example.com/items")
