"""Pipeline orchestration component for scraping, validating, and persisting FPL players."""

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.models.fpl_player import FPLPlayer
from src.scraper.fpl_scraper import FPLScraper
from src.storage.fpl_storage import FPLStorage
from src.storage.raw_storage import RawStorage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FPLPipelineResult:
    """Summary metrics of an FPL pipeline execution run."""

    records_extracted: int
    valid_records: int
    invalid_records: int
    records_persisted: int
    db_path: Path
    run_id: str | None


class FPLPipeline:
    """Orchestrates FPL extraction, Pydantic validation, and SQLite persistence."""

    def __init__(
        self,
        scraper: FPLScraper | None = None,
        storage: FPLStorage | None = None,
    ) -> None:
        """Initialize the FPLPipeline.

        Args:
            scraper: FPLScraper instance.
            storage: FPLStorage instance.
        """
        self.scraper = scraper or FPLScraper()
        self.storage = storage or FPLStorage()

    def validate_records(
        self, raw_records: list[dict[str, Any]]
    ) -> tuple[list[FPLPlayer], list[dict[str, Any]]]:
        """Validate raw extracted dictionaries against the Pydantic FPLPlayer model.

        Args:
            raw_records: List of raw extracted player dictionaries.

        Returns:
            Tuple of (valid_players, invalid_records_with_errors).
        """
        valid_players: list[FPLPlayer] = []
        invalid_records: list[dict[str, Any]] = []

        for idx, record in enumerate(raw_records, start=1):
            try:
                player = FPLPlayer(**record)
                valid_players.append(player)
            except ValidationError as err:
                logger.warning(
                    "FPL validation failed for record #%d (%s): %s",
                    idx,
                    record.get("web_name", "<unknown>"),
                    err.errors(),
                )
                invalid_records.append({"record": record, "errors": err.errors()})

        return valid_players, invalid_records

    def run(
        self,
        endpoint_url: str = FPLScraper.DEFAULT_BOOTSTRAP_URL,
        save_raw: bool = False,
    ) -> FPLPipelineResult:
        """Execute end-to-end extraction, validation, and persistence pipeline.

        Args:
            endpoint_url: Source API endpoint URL.
            save_raw: Whether to save raw JSON payload to disk.

        Returns:
            FPLPipelineResult with execution metrics.
        """
        logger.info("Starting FPL pipeline execution from %s", endpoint_url)

        # 1. Extraction Layer
        self.scraper.save_raw = save_raw
        if save_raw and not self.scraper.raw_storage:
            self.scraper.raw_storage = RawStorage()

        run_id = (
            self.scraper.raw_storage.generate_run_id(prefix="fpl")
            if save_raw and self.scraper.raw_storage
            else None
        )

        extracted_records = self.scraper.scrape(url=endpoint_url, run_id=run_id)

        # 2. Validation Layer
        valid_players, invalid_records = self.validate_records(extracted_records)

        # 3. Persistence Layer
        persisted_count = self.storage.insert_players(valid_players)

        logger.info(
            "FPL pipeline completed: %d extracted, %d valid, %d invalid, %d persisted",
            len(extracted_records),
            len(valid_players),
            len(invalid_records),
            persisted_count,
        )

        return FPLPipelineResult(
            records_extracted=len(extracted_records),
            valid_records=len(valid_players),
            invalid_records=len(invalid_records),
            records_persisted=persisted_count,
            db_path=self.storage.db_path,
            run_id=run_id,
        )


def run_fpl_pipeline_cli() -> None:
    """CLI runner for FPL pipeline."""
    parser = argparse.ArgumentParser(description="Run FPL Data Extraction, Validation & Persistence Pipeline.")
    parser.add_argument(
        "--url",
        default=FPLScraper.DEFAULT_BOOTSTRAP_URL,
        help=f"Source FPL endpoint (default: {FPLScraper.DEFAULT_BOOTSTRAP_URL})",
    )
    parser.add_argument(
        "--db-path",
        default="data/processed/fpl.db",
        help="Target SQLite database path (default: data/processed/fpl.db)",
    )
    parser.add_argument(
        "--save-raw",
        action="store_true",
        default=False,
        help="Save raw bootstrap JSON to data/raw/fpl/<run_id>/bootstrap.json",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed progress logging",
    )

    args = parser.parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    scraper = FPLScraper(endpoint_url=args.url, save_raw=args.save_raw)
    storage = FPLStorage(db_path=args.db_path)
    pipeline = FPLPipeline(scraper=scraper, storage=storage)

    result = pipeline.run(endpoint_url=args.url, save_raw=args.save_raw)

    print("\n" + "=" * 60)
    print("Fantasy Premier League (FPL) Pipeline Execution Summary")
    print("=" * 60)
    print(f"Source Endpoint:     {args.url}")
    print(f"Records Extracted:   {result.records_extracted}")
    print(f"Valid Records:       {result.valid_records}")
    print(f"Invalid Records:     {result.invalid_records}")
    print(f"Records Persisted:   {result.records_persisted}")
    print(f"Target Database:     {result.db_path}")
    if result.run_id:
        print(f"Raw Data Run ID:     {result.run_id}")
        print(f"Storage Directory:   data/raw/fpl/{result.run_id}/")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    from pathlib import Path
    import sys

    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    run_fpl_pipeline_cli()
