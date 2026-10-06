"""Base scraper abstraction defining the standard extraction workflow."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from bs4 import BeautifulSoup

from src.scraper.http_client import HTTPClient
from src.scraper.parser import parse_html

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base scraper defining the core extraction lifecycle.

    Lifecycle:
        fetch (URL) -> parse (HTML -> BeautifulSoup) -> extract (DOM -> Structured Data)
    """

    def __init__(self, client: HTTPClient | None = None) -> None:
        """Initialize base scraper with an HTTPClient instance."""
        self.client = client or HTTPClient()

    def fetch(self, url: str, **kwargs: Any) -> str:
        """Fetch raw HTML content from a given URL.

        Args:
            url: Target URL.
            **kwargs: Extra parameters passed to the HTTP client.

        Returns:
            The response text (HTML).
        """
        response = self.client.get(url, **kwargs)
        return response.text

    def parse(self, html_content: str) -> BeautifulSoup:
        """Parse raw HTML content into a BeautifulSoup document."""
        return parse_html(html_content)

    @abstractmethod
    def extract(self, soup: BeautifulSoup) -> Any:
        """Extract structured data from a parsed BeautifulSoup document.

        Must be implemented by concrete scrapers.

        Args:
            soup: Parsed BeautifulSoup DOM.

        Returns:
            Structured data (e.g. dict, list of dicts, domain model).
        """
        pass

    def scrape(self, url: str, **kwargs: Any) -> Any:
        """Execute the end-to-end extraction lifecycle for a given URL.

        Args:
            url: Target URL.
            **kwargs: Extra parameters for the fetch step.

        Returns:
            Extracted structured data.
        """
        logger.info("Executing scrape pipeline for %s", url)
        html_content = self.fetch(url, **kwargs)
        soup = self.parse(html_content)
        data = self.extract(soup)
        logger.info("Successfully finished scrape pipeline for %s", url)
        return data
