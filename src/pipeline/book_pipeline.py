"""Orchestration pipeline for scraping, validating, and persisting Book records."""

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.models.book import Book
from src.scraper.book_scraper import BookScraper
from src.storage.raw_storage import RawStorage
from src.storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    """Summary metrics of a pipeline execution run."""

    pages_scraped: int
    records_extracted: int
    valid_records: int
    invalid_records: int
    records_persisted: int
    db_path: Path
    run_id: str | None


class BookPipeline:
    """Orchestrates extraction, validation, and storage workflows for books."""

    def __init__(
        self,
        scraper: BookScraper | None = None,
        storage: SQLiteStorage | None = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            scraper: BookScraper instance (or default if None).
            storage: SQLiteStorage instance (or default if None).
        """
        self.scraper = scraper or BookScraper()
        self.storage = storage or SQLiteStorage()

    def validate_records(
        self, raw_records: list[dict[str, Any]]
    ) -> tuple[list[Book], list[dict[str, Any]]]:
        """Validate raw extracted dictionaries against the Pydantic Book model.

        Args:
            raw_records: List of raw extracted dictionaries.

        Returns:
            Tuple of (valid_book_models, invalid_record_errors).
        """
        valid_books: list[Book] = []
        invalid_records: list[dict[str, Any]] = []

        for idx, record in enumerate(raw_records, start=1):
            try:
                book = Book(**record)
                valid_books.append(book)
            except ValidationError as err:
                logger.warning(
                    "Validation failed for record #%d (%s): %s",
                    idx,
                    record.get("title", "<unknown>"),
                    err.errors(),
                )
                invalid_records.append({"record": record, "errors": err.errors()})

        return valid_books, invalid_records

    def run(
        self,
        start_url: str = BookScraper.DEFAULT_BASE_URL,
        max_pages: int = 1,
        save_raw: bool = False,
    ) -> PipelineResult:
        """Execute the end-to-end pipeline: scrape -> validate -> persist.

        Args:
            start_url: Starting catalog URL.
            max_pages: Maximum pages to scrape.
            save_raw: Whether to persist raw HTML to disk.

        Returns:
            PipelineResult with run metrics.
        """
        logger.info("Starting pipeline execution for %s (max_pages=%d)", start_url, max_pages)

        # 1. Extraction Layer
        self.scraper.save_raw = save_raw
        if save_raw and not self.scraper.raw_storage:
            self.scraper.raw_storage = RawStorage()

        run_id = (
            self.scraper.raw_storage.generate_run_id(prefix="books")
            if save_raw and self.scraper.raw_storage
            else None
        )

        extracted_records = self.scraper.scrape(
            url=start_url, max_pages=max_pages, run_id=run_id
        )

        # 2. Validation Layer
        valid_books, invalid_records = self.validate_records(extracted_records)

        # 3. Persistence Layer
        persisted_count = self.storage.insert_books(valid_books)

        pages_count = min(max_pages, max(1, (len(extracted_records) + 19) // 20)) if extracted_records else 0

        logger.info(
            "Pipeline completed: %d extracted, %d valid, %d invalid, %d persisted",
            len(extracted_records),
            len(valid_books),
            len(invalid_records),
            persisted_count,
        )

        return PipelineResult(
            pages_scraped=pages_count,
            records_extracted=len(extracted_records),
            valid_records=len(valid_books),
            invalid_records=len(invalid_records),
            records_persisted=persisted_count,
            db_path=self.storage.db_path,
            run_id=run_id,
        )


def run_pipeline_cli() -> None:
    """CLI runner for the Book Data Pipeline."""
    parser = argparse.ArgumentParser(
        description="Run Book Scraping, Validation & SQLite Persistence Pipeline."
    )
    parser.add_argument(
        "--url",
        default=BookScraper.DEFAULT_BASE_URL,
        help="Starting catalog URL (default: http://books.toscrape.com/)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="Maximum pages to scrape (default: 1)",
    )
    parser.add_argument(
        "--db-path",
        default="data/processed/books.db",
        help="Path to SQLite database (default: data/processed/books.db)",
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
        help="Enable verbose progress logging",
    )

    args = parser.parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    scraper = BookScraper(base_url=args.url, max_pages=args.max_pages, save_raw=args.save_raw)
    storage = SQLiteStorage(db_path=args.db_path)
    pipeline = BookPipeline(scraper=scraper, storage=storage)

    result = pipeline.run(start_url=args.url, max_pages=args.max_pages, save_raw=args.save_raw)

    print("\n" + "=" * 60)
    print("Book Data Pipeline Execution Summary")
    print("=" * 60)
    print(f"Pages scraped:       {result.pages_scraped}")
    print(f"Records extracted:   {result.records_extracted}")
    print(f"Valid records:       {result.valid_records}")
    print(f"Invalid records:     {result.invalid_records}")
    print(f"Records persisted:   {result.records_persisted}")
    print(f"Database:            {result.db_path}")
    if result.run_id:
        print(f"Raw data run ID:     {result.run_id}")
    print("=" * 60)


if __name__ == "__main__":
    from pathlib import Path
    import sys

    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    run_pipeline_cli()
