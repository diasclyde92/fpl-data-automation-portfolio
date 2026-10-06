"""Scraper package exports."""

from src.scraper.base_scraper import BaseScraper
from src.scraper.exceptions import ParsingError, RequestError, ScraperError
from src.scraper.http_client import HTTPClient
from src.scraper.parser import parse_html

__all__ = [
    "BaseScraper",
    "HTTPClient",
    "ScraperError",
    "RequestError",
    "ParsingError",
    "parse_html",
]
