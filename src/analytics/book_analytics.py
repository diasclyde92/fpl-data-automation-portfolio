"""Analytics layer for computing statistics, rankings, and data quality on persisted books."""

import argparse
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger(__name__)

# Canonical columns and types expected from the books table
EXPECTED_COLUMNS = [
    "id",
    "title",
    "price",
    "rating",
    "availability",
    "detail_url",
    "scraped_at",
]


@dataclass(frozen=True)
class SummaryStats:
    """Core descriptive statistics for book prices and ratings."""

    total_books: int
    average_price: float | None
    median_price: float | None
    min_price: float | None
    max_price: float | None
    average_rating: float | None


@dataclass(frozen=True)
class QualityReport:
    """Data quality diagnostics for persisted book records."""

    total_records: int
    missing_ratings: int
    missing_availability: int
    missing_prices: int
    duplicate_urls: int
    is_empty: bool


@dataclass(frozen=True)
class AnalyticsResult:
    """Comprehensive analytical metrics bundle ready for reporting layers."""

    summary: SummaryStats
    quality: QualityReport
    rating_distribution: dict[int, int]
    availability_distribution: dict[str, int]
    top_expensive: list[dict[str, Any]]
    bottom_expensive: list[dict[str, Any]]
    top_rated: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        return asdict(self)


class BookAnalytics:
    """Performs analytical transformations and aggregations on SQLite book data."""

    def __init__(self, storage: SQLiteStorage | None = None, db_path: Path | str = "data/processed/books.db") -> None:
        """Initialize BookAnalytics with a storage reader or database path.

        Args:
            storage: Optional SQLiteStorage instance.
            db_path: Path to database if storage is not provided.
        """
        self.storage = storage or SQLiteStorage(db_path=db_path)

    def load_data(self) -> pd.DataFrame:
        """Load books table from SQLite into a structured, typed Pandas DataFrame.

        Returns:
            pd.DataFrame with normalized types and parsed timestamps.
        """
        records = self.storage.get_all_books()
        if not records:
            logger.info("Database at %s contains no records. Returning empty DataFrame.", self.storage.db_path)
            empty_df = pd.DataFrame(columns=EXPECTED_COLUMNS)
            # Ensure correct dtypes on empty df
            empty_df["id"] = empty_df["id"].astype("int64", errors="ignore")
            empty_df["price"] = empty_df["price"].astype("float64", errors="ignore")
            empty_df["rating"] = empty_df["rating"].astype("Int64", errors="ignore")
            return empty_df

        df = pd.DataFrame(records)

        # Enforce appropriate data types
        df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("int64")
        df["price"] = pd.to_numeric(df["price"], errors="coerce").astype("float64")
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce").astype("Int64")
        df["title"] = df["title"].astype(str)
        df["availability"] = df["availability"].astype(str)
        df["detail_url"] = df["detail_url"].astype(str)
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True, errors="coerce")

        logger.info("Loaded %d book records into DataFrame from %s", len(df), self.storage.db_path)
        return df

    def get_summary_statistics(self, df: pd.DataFrame) -> SummaryStats:
        """Compute key summary statistics on books DataFrame.

        Args:
            df: Books DataFrame.

        Returns:
            SummaryStats dataclass.
        """
        if df.empty:
            return SummaryStats(
                total_books=0,
                average_price=None,
                median_price=None,
                min_price=None,
                max_price=None,
                average_rating=None,
            )

        total_books = len(df)
        valid_prices = df["price"].dropna()
        valid_ratings = df["rating"].dropna()

        avg_price = round(float(valid_prices.mean()), 2) if not valid_prices.empty else None
        median_price = round(float(valid_prices.median()), 2) if not valid_prices.empty else None
        min_price = round(float(valid_prices.min()), 2) if not valid_prices.empty else None
        max_price = round(float(valid_prices.max()), 2) if not valid_prices.empty else None
        avg_rating = round(float(valid_ratings.mean()), 2) if not valid_ratings.empty else None

        return SummaryStats(
            total_books=total_books,
            average_price=avg_price,
            median_price=median_price,
            min_price=min_price,
            max_price=max_price,
            average_rating=avg_rating,
        )

    def get_rating_distribution(self, df: pd.DataFrame) -> dict[int, int]:
        """Compute frequency distribution of star ratings (1 to 5).

        Args:
            df: Books DataFrame.

        Returns:
            Dict mapping rating integer to count.
        """
        if df.empty or df["rating"].dropna().empty:
            return {}

        counts = df["rating"].dropna().value_counts().sort_index()
        return {int(rating): int(count) for rating, count in counts.items()}

    def get_availability_distribution(self, df: pd.DataFrame) -> dict[str, int]:
        """Compute counts per availability status.

        Args:
            df: Books DataFrame.

        Returns:
            Dict mapping status string to count.
        """
        if df.empty:
            return {}

        counts = df["availability"].value_counts()
        return {str(status): int(count) for status, count in counts.items()}

    def get_top_expensive(self, df: pd.DataFrame, n: int = 5) -> list[dict[str, Any]]:
        """Retrieve the top N highest-priced books.

        Args:
            df: Books DataFrame.
            n: Number of items.

        Returns:
            List of dictionary records.
        """
        if df.empty:
            return []

        top_df = df.dropna(subset=["price"]).nlargest(n, "price")[
            ["title", "price", "rating", "availability", "detail_url"]
        ]
        return top_df.to_dict(orient="records")

    def get_bottom_expensive(self, df: pd.DataFrame, n: int = 5) -> list[dict[str, Any]]:
        """Retrieve the bottom N lowest-priced books.

        Args:
            df: Books DataFrame.
            n: Number of items.

        Returns:
            List of dictionary records.
        """
        if df.empty:
            return []

        bottom_df = df.dropna(subset=["price"]).nsmallest(n, "price")[
            ["title", "price", "rating", "availability", "detail_url"]
        ]
        return bottom_df.to_dict(orient="records")

    def get_top_rated(self, df: pd.DataFrame, n: int = 5) -> list[dict[str, Any]]:
        """Retrieve top N highest-rated books, breaking ties by price descending.

        Args:
            df: Books DataFrame.
            n: Number of items.

        Returns:
            List of dictionary records.
        """
        if df.empty:
            return []

        top_rated_df = (
            df.dropna(subset=["rating"])
            .sort_values(by=["rating", "price"], ascending=[False, False])
            .head(n)[["title", "price", "rating", "availability", "detail_url"]]
        )
        return top_rated_df.to_dict(orient="records")

    def get_quality_report(self, df: pd.DataFrame) -> QualityReport:
        """Run data quality analysis over the dataset.

        Args:
            df: Books DataFrame.

        Returns:
            QualityReport dataclass.
        """
        if df.empty:
            return QualityReport(
                total_records=0,
                missing_ratings=0,
                missing_availability=0,
                missing_prices=0,
                duplicate_urls=0,
                is_empty=True,
            )

        total_records = len(df)
        missing_ratings = int(df["rating"].isna().sum())
        missing_avail = int((df["availability"].isna() | (df["availability"].str.strip() == "")).sum())
        missing_prices = int(df["price"].isna().sum())
        duplicate_urls = int(df["detail_url"].duplicated().sum())

        return QualityReport(
            total_records=total_records,
            missing_ratings=missing_ratings,
            missing_availability=missing_avail,
            missing_prices=missing_prices,
            duplicate_urls=duplicate_urls,
            is_empty=False,
        )

    def analyze(self) -> AnalyticsResult:
        """Execute full analytical pipeline and produce an AnalyticsResult bundle.

        Returns:
            AnalyticsResult dataclass.
        """
        df = self.load_data()
        return AnalyticsResult(
            summary=self.get_summary_statistics(df),
            quality=self.get_quality_report(df),
            rating_distribution=self.get_rating_distribution(df),
            availability_distribution=self.get_availability_distribution(df),
            top_expensive=self.get_top_expensive(df, n=5),
            bottom_expensive=self.get_bottom_expensive(df, n=5),
            top_rated=self.get_top_rated(df, n=5),
        )


def run_analytics_cli() -> None:
    """CLI runner for book analytics."""
    parser = argparse.ArgumentParser(description="Analyze scraped books stored in SQLite database.")
    parser.add_argument(
        "--db-path",
        default="data/processed/books.db",
        help="Path to SQLite database (default: data/processed/books.db)",
    )
    args = parser.parse_args()

    analytics = BookAnalytics(db_path=args.db_path)
    result = analytics.analyze()
    summary = result.summary
    quality = result.quality

    print("\n" + "=" * 60)
    print("Book Analytics & Business Intelligence")
    print("=" * 60)
    print(f"Database:          {args.db_path}")
    print(f"Total Books:       {summary.total_books}")
    print(f"Average Price:     GBP {summary.average_price:.2f}" if summary.average_price is not None else "Average Price:     N/A")
    print(f"Median Price:      GBP {summary.median_price:.2f}" if summary.median_price is not None else "Median Price:      N/A")
    print(f"Minimum Price:     GBP {summary.min_price:.2f}" if summary.min_price is not None else "Minimum Price:     N/A")
    print(f"Maximum Price:     GBP {summary.max_price:.2f}" if summary.max_price is not None else "Maximum Price:     N/A")
    print(f"Average Rating:    {summary.average_rating:.2f}/5" if summary.average_rating is not None else "Average Rating:    N/A")
    print("=" * 60)

    print("\nRating Distribution:")
    if result.rating_distribution:
        for stars in sorted(result.rating_distribution.keys()):
            bar = "*" * stars + "-" * (5 - stars)
            print(f"  [{bar}] {stars} Star: {result.rating_distribution[stars]} books")
    else:
        print("  (No ratings available)")

    print("\nTop 5 Most Expensive Books:")
    if result.top_expensive:
        for idx, book in enumerate(result.top_expensive, start=1):
            rating_str = f"{book['rating']}/5 stars" if pd.notna(book['rating']) else "Unrated"
            print(f"  [{idx}] GBP {book['price']:.2f} -- {book['title']} ({rating_str})")
    else:
        print("  (No records)")

    print("\nTop 5 Least Expensive Books:")
    if result.bottom_expensive:
        for idx, book in enumerate(result.bottom_expensive, start=1):
            rating_str = f"{book['rating']}/5 stars" if pd.notna(book['rating']) else "Unrated"
            print(f"  [{idx}] GBP {book['price']:.2f} -- {book['title']} ({rating_str})")
    else:
        print("  (No records)")

    print("\nData Quality Report:")
    print(f"  Missing Ratings:      {quality.missing_ratings}")
    print(f"  Missing Prices:       {quality.missing_prices}")
    print(f"  Missing Availability: {quality.missing_availability}")
    print(f"  Duplicate URLs:       {quality.duplicate_urls}")
    print(f"  Dataset Status:       {'EMPTY' if quality.is_empty else 'HEALTHY'}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    from pathlib import Path
    import sys

    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    run_analytics_cli()
