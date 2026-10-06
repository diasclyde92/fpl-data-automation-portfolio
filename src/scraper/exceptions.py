"""Custom exception hierarchy for the scraping framework."""


class ScraperError(Exception):
    """Base exception for all errors within the scraper package."""

    pass


class RequestError(ScraperError):
    """Raised when an HTTP request encounters a failure (e.g. connection, timeout, status code)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ParsingError(ScraperError):
    """Raised when an error occurs during parsing or data extraction from HTML content."""

    pass
