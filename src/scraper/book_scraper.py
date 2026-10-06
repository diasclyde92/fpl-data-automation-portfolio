"""Concrete scraper implementation for Books to Scrape (books.toscrape.com).

Demonstrates the BaseScraper lifecycle against a real-world web target,
with pagination traversal and optional raw HTML response preservation.
"""

import argparse
import logging
import re
import sys
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from src.scraper.base_scraper import BaseScraper
from src.scraper.http_client import HTTPClient
from src.storage.raw_storage import RawStorage

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
    """Scrapes structured book listing records from books.toscrape.com with pagination support."""

    DEFAULT_BASE_URL = "http://books.toscrape.com/"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        max_pages: int = 5,
        save_raw: bool = False,
        raw_storage: RawStorage | None = None,
        client: HTTPClient | None = None,
    ) -> None:
        """Initialize the BookScraper.

        Args:
            base_url: Root URL used to resolve relative links.
            max_pages: Maximum number of catalog pages to traverse.
            save_raw: Whether to persist raw HTML to disk.
            raw_storage: Optional RawStorage instance for raw response preservation.
            client: Optional HTTPClient instance.
        """
        super().__init__(client=client)
        self.base_url = base_url
        self.max_pages = max_pages
        self.save_raw = save_raw
        self.raw_storage = raw_storage or (RawStorage() if save_raw else None)

    def extract(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract structured book records from parsed HTML of a single page.

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
            availability = " ".join(avail_tag.get_text().split())

        return {
            "title": title.strip(),
            "price": price,
            "rating": rating,
            "availability": availability,
            "detail_url": detail_url,
        }

    def get_next_page_url(self, soup: BeautifulSoup, current_url: str) -> str | None:
        """Find and normalize the next page URL from pagination controls.

        Args:
            soup: Parsed BeautifulSoup document.
            current_url: URL of the current page for resolving relative links.

        Returns:
            Normalized absolute URL for the next page, or None if not found.
        """
        next_li = soup.find("li", class_="next")
        if not next_li:
            return None

        next_a = next_li.find("a")
        if not next_a:
            return None

        href = next_a.get("href")
        if not href or not isinstance(href, str):
            return None

        # books.toscrape.com uses relative URLs like 'page-2.html' or 'catalogue/page-2.html'
        return urljoin(current_url, href)

    def scrape(
        self,
        url: str | None = None,
        max_pages: int | None = None,
        run_id: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Scrape structured records traversing pagination up to max_pages.

        Args:
            url: Starting URL. Defaults to self.base_url.
            max_pages: Page limit override. Defaults to self.max_pages.
            run_id: Optional run identifier for raw data preservation.
            **kwargs: Extra parameters passed to the fetch step.

        Returns:
            List of all extracted records across traversed pages.
        """
        current_url: str | None = url or self.base_url
        effective_max = max_pages if max_pages is not None else self.max_pages

        all_records: list[dict[str, Any]] = []
        visited_urls: set[str] = set()
        page_count = 0

        actual_run_id = (
            run_id
            or (self.raw_storage.generate_run_id(prefix="books") if self.raw_storage else None)
        )

        while current_url and page_count < effective_max:
            if current_url in visited_urls:
                logger.warning("Pagination loop detected for URL: %s. Halting pagination.", current_url)
                break

            visited_urls.add(current_url)
            page_count += 1
            logger.info("Scraping page %d: %s", page_count, current_url)

            html_content = self.fetch(current_url, **kwargs)

            # Persist raw HTML if enabled
            if self.save_raw and self.raw_storage and actual_run_id:
                self.raw_storage.save_page(
                    dataset="books",
                    run_id=actual_run_id,
                    page_number=page_count,
                    html_content=html_content,
                )

            soup = self.parse(html_content)
            page_records = self.extract(soup)
            logger.info("Extracted %d records from page %d", len(page_records), page_count)
            all_records.extend(page_records)

            # Find next page
            next_url = self.get_next_page_url(soup, current_url)
            if next_url:
                logger.info("Next page detected: %s", next_url)
                current_url = next_url
            else:
                logger.info("No next page link found; reached end of catalog.")
                break

        if page_count >= effective_max and current_url:
            logger.info("Reached configured maximum page limit (%d pages).", effective_max)

        logger.info("Pagination completed. Total records extracted: %d across %d pages.", len(all_records), page_count)
        return all_records


def run_cli() -> None:
    """CLI runner supporting page limits and raw storage options."""
    parser = argparse.ArgumentParser(description="Scrape Books to Scrape catalog with pagination and raw storage.")
    parser.add_argument(
        "--url",
        default=BookScraper.DEFAULT_BASE_URL,
        help="Starting catalog URL (default: http://books.toscrape.com/)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="Maximum number of pages to scrape (default: 1)",
    )
    parser.add_argument(
        "--save-raw",
        action="store_true",
        default=False,
        help="Save raw HTML responses under data/raw/books/<run_id>/",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging output",
    )

    args = parser.parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    raw_storage = RawStorage() if args.save_raw else None
    run_id = raw_storage.generate_run_id(prefix="books") if raw_storage else None

    scraper = BookScraper(
        base_url=args.url,
        max_pages=args.max_pages,
        save_raw=args.save_raw,
        raw_storage=raw_storage,
    )

    records = scraper.scrape(url=args.url, max_pages=args.max_pages, run_id=run_id)

    # Concise CLI summary
    print("\n" + "=" * 60)
    print("Scrape Execution Summary")
    print("=" * 60)
    print(f"Target URL:        {args.url}")
    print(f"Max Pages Limit:   {args.max_pages}")
    print(f"Records Extracted: {len(records)}")
    print(f"Raw Data Saved:    {'yes' if args.save_raw else 'no'}")
    if args.save_raw and run_id:
        print(f"Run ID:            {run_id}")
        print(f"Storage Directory: data/raw/books/{run_id}/")
    print("=" * 60)

    sample_size = min(3, len(records))
    if sample_size > 0:
        print(f"\nShowing Sample of {sample_size} Records:\n")
        for idx, record in enumerate(records[:sample_size], start=1):
            price_str = f"GBP {record['price']:.2f}" if record['price'] is not None else "N/A"
            print(f"[{idx}] {record['title']} | Price: {price_str} | Rating: {record['rating']}/5")
        print()


if __name__ == "__main__":
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    run_cli()
