"""Concrete scraper implementation for Books to Scrape (books.toscrape.com).

Demonstrates the BaseScraper lifecycle against a real-world web target.
"""

import logging
import re
import sys
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from src.scraper.base_scraper import BaseScraper
from src.scraper.http_client import HTTPClient

logger = logging.getLogger(__name__)

# Mapping text representation of star ratings to integer numbers
RATING_MAP = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


class BookScraper(BaseScraper):
    """Scrapes structured book listing records from books.toscrape.com."""

    DEFAULT_BASE_URL = "http://books.toscrape.com/"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        client: HTTPClient | None = None,
    ) -> None:
        """Initialize the BookScraper.

        Args:
            base_url: Root URL used to resolve relative links.
            client: Optional HTTPClient instance.
        """
        super().__init__(client=client)
        self.base_url = base_url

    def extract(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract structured book records from parsed HTML.

        Args:
            soup: Parsed BeautifulSoup document.

        Returns:
            List of extracted book item dictionaries.
        """
        records: list[dict[str, Any]] = []
        product_pods = soup.find_all("article", class_="product_pod")

        for pod in product_pods:
            if not isinstance(pod, Tag):
                continue

            record = self._extract_pod(pod)
            if record:
                records.append(record)

        logger.info("Extracted %d book records from page", len(records))
        return records

    def _extract_pod(self, pod: Tag) -> dict[str, Any] | None:
        """Extract and normalize data from a single product_pod element.

        Args:
            pod: BeautifulSoup Tag for an article.product_pod.

        Returns:
            Normalized dictionary or None if mandatory title/URL cannot be identified.
        """
        # 1. Title & Detail URL
        title_tag = pod.find("h3")
        a_tag = title_tag.find("a") if title_tag else None

        if not a_tag:
            logger.warning("Skipping pod: missing title anchor tag")
            return None

        # Title attribute on anchor tag contains full unabridged title
        title = a_tag.get("title") or a_tag.get_text(strip=True)
        if not title:
            return None

        raw_href = a_tag.get("href", "")
        detail_url = urljoin(self.base_url, raw_href) if raw_href else None

        # 2. Price (GBP)
        price: float | None = None
        price_tag = pod.find("p", class_="price_color")
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            # Match numeric portion: e.g. "£51.77" or "Â£51.77" -> 51.77
            match = re.search(r"(\d+(?:\.\d+)?)", price_text)
            if match:
                try:
                    price = float(match.group(1))
                except ValueError:
                    price = None

        # 3. Rating (1-5 integer)
        rating: int | None = None
        rating_tag = pod.find("p", class_=re.compile(r"star-rating", re.I))
        if rating_tag:
            classes = rating_tag.get("class", [])
            for cls in classes:
                cls_lower = cls.lower()
                if cls_lower in RATING_MAP:
                    rating = RATING_MAP[cls_lower]
                    break

        # 4. Availability
        availability: str = "Unknown"
        avail_tag = pod.find("p", class_="availability")
        if avail_tag:
            # Strip excessive whitespace / newlines
            availability = " ".join(avail_tag.get_text().split())

        return {
            "title": title.strip(),
            "price": price,
            "rating": rating,
            "availability": availability,
            "detail_url": detail_url,
        }


def run_demo(target_url: str = BookScraper.DEFAULT_BASE_URL) -> None:
    """CLI demo runner for BookScraper."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 70)
    print("Executing BookScraper Demo (Phase 3)")
    print(f"Target URL: {target_url}")
    print("=" * 70)

    scraper = BookScraper()
    records = scraper.scrape(target_url)

    print("\n" + "=" * 70)
    print(f"Scrape Complete: Extracted {len(records)} records.")
    print("=" * 70)

    sample_size = min(3, len(records))
    print(f"\nShowing Sample of {sample_size} Extracted Records:\n")

    for idx, record in enumerate(records[:sample_size], start=1):
        print(f"[{idx}] {record['title']}")
        print(f"    Price: GBP {record['price']:.2f}" if record['price'] is not None else "    Price: N/A")
        print(f"    Rating: {record['rating']}/5 stars")
        print(f"    Availability: {record['availability']}")
        print(f"    URL: {record['detail_url']}")
        print()


if __name__ == "__main__":
    from pathlib import Path

    # Ensure project root in sys.path when executed directly
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    target = sys.argv[1] if len(sys.argv) > 1 else BookScraper.DEFAULT_BASE_URL
    run_demo(target)
