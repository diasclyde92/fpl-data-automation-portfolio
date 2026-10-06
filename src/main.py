"""Main application entry point.

Initializes and validates the project execution environment.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.scraper import BaseScraper, HTTPClient, ScraperError  # noqa: E402


def main() -> None:
    """Run project initialization check and verify scraping framework imports."""
    print("=" * 60)
    print("Web Scraping & Data Automation Pipeline")
    print("Status: Project initialized successfully (Phase 2).")
    print(f"Python Runtime: {sys.version.split()[0]}")
    print("Core Components Verified: HTTPClient, BaseScraper, ScraperError")
    print("=" * 60)


if __name__ == "__main__":
    main()
