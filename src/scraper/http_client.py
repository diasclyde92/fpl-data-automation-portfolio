"""HTTP client module for robust and resilient web scraping requests."""

import logging
import time
from typing import Any

import requests
from requests.exceptions import RequestException

from src.scraper.exceptions import RequestError

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class HTTPClient:
    """Manages HTTP requests with timeouts, default headers, and transient error retry logic."""

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        headers: dict[str, str] | None = None,
        session: requests.Session | None = None,
    ) -> None:
        """Initialize the HTTPClient.

        Args:
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts for transient errors.
            backoff_factor: Multiplier for exponential backoff delay between retries.
            headers: Optional default headers to merge with defaults.
            session: Optional custom requests Session.
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = session or requests.Session()

        # Set default headers
        default_headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if headers:
            default_headers.update(headers)
        self.session.headers.update(default_headers)

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """Perform an HTTP GET request with retry handling for transient failures.

        Args:
            url: Target URL.
            **kwargs: Additional parameters passed to requests.Session.get.

        Returns:
            requests.Response object on success.

        Raises:
            RequestError: If the request fails after maximum retries or on a fatal client error.
        """
        timeout = kwargs.pop("timeout", self.timeout)
        attempts = 0

        while True:
            attempts += 1
            logger.info("Request started: GET %s (attempt %d/%d)", url, attempts, self.max_retries + 1)

            try:
                response = self.session.get(url, timeout=timeout, **kwargs)

                # Check if status code indicates a transient failure
                if response.status_code in TRANSIENT_STATUS_CODES and attempts <= self.max_retries:
                    retry_delay = self.backoff_factor * (2 ** (attempts - 1))
                    logger.warning(
                        "Transient HTTP %d received for %s. Retrying in %.1fs (attempt %d/%d)...",
                        response.status_code,
                        url,
                        retry_delay,
                        attempts,
                        self.max_retries,
                    )
                    time.sleep(retry_delay)
                    continue

                # Raise HTTPError for any non-2xx status code
                response.raise_for_status()

                logger.info("Request succeeded: GET %s [%d]", url, response.status_code)
                return response

            except (requests.ConnectionError, requests.Timeout) as exc:
                if attempts <= self.max_retries:
                    retry_delay = self.backoff_factor * (2 ** (attempts - 1))
                    logger.warning(
                        "Transient network error (%s) requesting %s. Retrying in %.1fs (attempt %d/%d)...",
                        type(exc).__name__,
                        url,
                        retry_delay,
                        attempts,
                        self.max_retries,
                    )
                    time.sleep(retry_delay)
                    continue

                logger.error("Request failed: GET %s exhausted retries: %s", url, exc)
                raise RequestError(f"Request failed for {url} after {attempts} attempts: {exc}") from exc

            except requests.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                logger.error("Request failed: GET %s with HTTP %s", url, status_code)
                raise RequestError(
                    f"HTTP {status_code} error fetching {url}", status_code=status_code
                ) from exc

            except RequestException as exc:
                logger.error("Request failed: GET %s unexpected request error: %s", url, exc)
                raise RequestError(f"Unexpected request error for {url}: {exc}") from exc

    def close(self) -> None:
        """Close the underlying requests session."""
        self.session.close()
