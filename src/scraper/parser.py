"""HTML parsing helper using BeautifulSoup."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from src.scraper.exceptions import ParsingError

logger = logging.getLogger(__name__)


def parse_html(html_content: str, parser: str = "html.parser") -> BeautifulSoup:
    """Parse raw HTML string into a BeautifulSoup DOM tree.

    Args:
        html_content: Raw HTML text to parse.
        parser: Parser backend to use. Defaults to standard library 'html.parser'.

    Returns:
        BeautifulSoup parsed document.

    Raises:
        ParsingError: If HTML parsing fails unexpectedly.
    """
    if not isinstance(html_content, str):
        raise ParsingError(f"Expected str for html_content, got {type(html_content).__name__}")

    try:
        soup = BeautifulSoup(html_content, parser)
        return soup
    except Exception as exc:
        logger.error("Failed to parse HTML content: %s", exc)
        raise ParsingError(f"Failed to parse HTML: {exc}") from exc
