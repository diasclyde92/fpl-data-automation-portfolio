"""Storage layer for persisting raw scraping responses."""

import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class RawStorage:
    """Manages raw HTML response preservation under data/raw/<dataset>/<run_id>/."""

    def __init__(self, base_dir: Path | str = "data/raw") -> None:
        """Initialize RawStorage.

        Args:
            base_dir: Root directory for raw artifact storage.
        """
        self.base_dir = Path(base_dir)

    def generate_run_id(self, prefix: str = "") -> str:
        """Generate a timestamped run ID.

        Args:
            prefix: Optional prefix string.

        Returns:
            String run identifier formatted as [prefix_]YYYYMMDD_HHMMSS.
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}" if prefix else timestamp

    def get_run_dir(self, dataset: str, run_id: str) -> Path:
        """Get the specific run directory Path and ensure it exists.

        Args:
            dataset: Dataset or scraper name (e.g. 'books').
            run_id: Unique run identifier.

        Returns:
            Path object pointing to the directory.
        """
        run_path = self.base_dir / dataset / run_id
        run_path.mkdir(parents=True, exist_ok=True)
        return run_path

    def save_page(self, dataset: str, run_id: str, page_number: int, html_content: str) -> Path:
        """Save raw HTML content for a scraped page.

        Args:
            dataset: Dataset category name.
            run_id: Unique identifier for the scraping run.
            page_number: 1-indexed page sequence number.
            html_content: Raw HTML text string.

        Returns:
            Path of the saved file.

        Raises:
            OSError: If writing to the filesystem fails.
        """
        run_dir = self.get_run_dir(dataset, run_id)
        filename = f"page_{page_number:03d}.html"
        target_path = run_dir / filename

        try:
            target_path.write_text(html_content, encoding="utf-8")
            logger.info("Saved raw HTML: %s (%d bytes)", target_path, len(html_content))
            return target_path
        except OSError as exc:
            logger.error("Failed to write raw HTML to %s: %s", target_path, exc)
            raise
