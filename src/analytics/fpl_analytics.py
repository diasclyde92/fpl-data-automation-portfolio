"""Analytics layer for computing statistics, value metrics, rankings, and quality audits on FPL player data."""

import argparse
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.storage.fpl_storage import FPLStorage

logger = logging.getLogger(__name__)

EXPECTED_FPL_COLUMNS = [
    "id",
    "first_name",
    "second_name",
    "web_name",
    "team",
    "position",
    "price",
    "total_points",
    "event_points",
    "selected_by_percent",
    "goals",
    "assists",
    "clean_sheets",
    "minutes",
    "bonus",
    "form",
    "status",
    "scraped_at",
]


@dataclass(frozen=True)
class FPLSummaryStats:
    """Core descriptive statistics for FPL players."""

    total_players: int
    average_price: float | None
    median_price: float | None
    min_price: float | None
    max_price: float | None
    total_goals_scored: int
    total_assists_provided: int
    average_points: float | None
    total_points: int = 0
    highest_points: int | None = None
    average_ownership: float | None = None


@dataclass(frozen=True)
class FPLQualityReport:
    """Data quality diagnostics for persisted FPL records."""

    total_records: int
    missing_prices: int
    missing_teams: int
    missing_positions: int
    duplicate_ids: int
    is_empty: bool


@dataclass(frozen=True)
class FPLAnalyticsResult:
    """Structured analytical metrics bundle ready for dashboard and reporting consumers."""

    summary: FPLSummaryStats
    quality: FPLQualityReport
    top_points: list[dict[str, Any]]
    top_value: list[dict[str, Any]]
    top_form: list[dict[str, Any]]
    top_selected: list[dict[str, Any]]
    top_goalscorers: list[dict[str, Any]]
    top_assists: list[dict[str, Any]]
    position_distribution: dict[str, int]
    team_distribution: dict[str, int]
    points_by_position: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        return asdict(self)


class FPLAnalytics:
    """Performs analytical transformations, player rankings, and aggregations on FPL data."""

    def __init__(self, storage: FPLStorage | None = None, db_path: Path | str = "data/processed/fpl.db") -> None:
        """Initialize FPLAnalytics with a storage reader or database path.

        Args:
            storage: Optional FPLStorage instance.
            db_path: Path to database if storage is not provided.
        """
        self.storage = storage or FPLStorage(db_path=db_path)

    def load_data(self) -> pd.DataFrame:
        """Load fpl_players table into a structured, typed Pandas DataFrame.

        Returns:
            pd.DataFrame with normalized types and computed value metrics.
        """
        records = self.storage.get_all_players()
        if not records:
            logger.info("FPL database at %s has no records. Returning empty DataFrame.", self.storage.db_path)
            empty_df = pd.DataFrame(columns=EXPECTED_FPL_COLUMNS + ["points_per_million", "points_per_90"])
            return empty_df

        df = pd.DataFrame(records)

        # Enforce appropriate data types
        df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("int64")
        df["price"] = pd.to_numeric(df["price"], errors="coerce").astype("float64")
        df["total_points"] = pd.to_numeric(df["total_points"], errors="coerce").astype("int64")
        df["event_points"] = pd.to_numeric(df["event_points"], errors="coerce").astype("int64")
        df["selected_by_percent"] = pd.to_numeric(df["selected_by_percent"], errors="coerce").astype("float64")
        df["goals"] = pd.to_numeric(df["goals"], errors="coerce").astype("int64")
        df["assists"] = pd.to_numeric(df["assists"], errors="coerce").astype("int64")
        df["clean_sheets"] = pd.to_numeric(df["clean_sheets"], errors="coerce").astype("int64")
        df["minutes"] = pd.to_numeric(df["minutes"], errors="coerce").astype("int64")
        df["bonus"] = pd.to_numeric(df["bonus"], errors="coerce").astype("int64")
        df["form"] = pd.to_numeric(df["form"], errors="coerce").astype("float64")
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True, errors="coerce")

        # Computed Advanced Metrics
        # 1. Points per million (Value efficiency)
        df["points_per_million"] = (df["total_points"] / df["price"].replace(0, pd.NA)).round(2).fillna(0.0)

        # 2. Points per 90 minutes (Production efficiency, for players with >= 90 mins)
        df["points_per_90"] = (
            df.apply(
                lambda r: round((r["total_points"] / (r["minutes"] / 90.0)), 2) if r["minutes"] >= 90 else 0.0,
                axis=1,
            )
        )

        logger.info("Loaded %d FPL players into DataFrame from %s", len(df), self.storage.db_path)
        return df

    def get_summary_statistics(self, df: pd.DataFrame) -> FPLSummaryStats:
        """Compute key aggregate summary statistics across all players.

        Args:
            df: Players DataFrame.

        Returns:
            FPLSummaryStats dataclass.
        """
        if df.empty:
            return FPLSummaryStats(
                total_players=0,
                average_price=None,
                median_price=None,
                min_price=None,
                max_price=None,
                total_goals_scored=0,
                total_assists_provided=0,
                average_points=None,
                total_points=0,
                highest_points=None,
                average_ownership=None,
            )

        total_players = len(df)
        prices = df["price"].dropna()
        points = df["total_points"].dropna()
        ownership = df["selected_by_percent"].dropna() if "selected_by_percent" in df.columns else pd.Series(dtype=float)

        avg_price = round(float(prices.mean()), 2) if not prices.empty else None
        med_price = round(float(prices.median()), 2) if not prices.empty else None
        min_price = round(float(prices.min()), 2) if not prices.empty else None
        max_price = round(float(prices.max()), 2) if not prices.empty else None
        tot_points = int(points.sum()) if not points.empty else 0
        avg_points = round(float(points.mean()), 2) if not points.empty else None
        highest_points = int(points.max()) if not points.empty else None
        avg_ownership = round(float(ownership.mean()), 2) if not ownership.empty else None
        total_goals = int(df["goals"].sum())
        total_assists = int(df["assists"].sum())

        return FPLSummaryStats(
            total_players=total_players,
            average_price=avg_price,
            median_price=med_price,
            min_price=min_price,
            max_price=max_price,
            total_goals_scored=total_goals,
            total_assists_provided=total_assists,
            average_points=avg_points,
            total_points=tot_points,
            highest_points=highest_points,
            average_ownership=avg_ownership,
        )

    def get_top_by_column(
        self, df: pd.DataFrame, column: str, n: int = 5, ascending: bool = False
    ) -> list[dict[str, Any]]:
        """Retrieve top N players by specific metric column.

        Args:
            df: Players DataFrame.
            column: Sort column.
            n: Number of records.
            ascending: Sort direction.

        Returns:
            List of dictionary player records.
        """
        if df.empty or column not in df.columns:
            return []

        cols = [
            "id",
            "web_name",
            "team",
            "position",
            "price",
            "total_points",
            "goals",
            "assists",
            "selected_by_percent",
            "form",
            "points_per_million",
        ]
        available_cols = [c for c in cols if c in df.columns]

        top_df = df.sort_values(by=column, ascending=ascending).head(n)[available_cols]
        return top_df.to_dict(orient="records")

    def get_position_distribution(self, df: pd.DataFrame) -> dict[str, int]:
        """Compute counts of players by position.

        Args:
            df: Players DataFrame.

        Returns:
            Dict mapping position to count.
        """
        if df.empty:
            return {}
        counts = df["position"].value_counts()
        return {str(pos): int(cnt) for pos, cnt in counts.items()}

    def get_position_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute aggregated metrics by position: player count, total points, avg points, avg price.

        Args:
            df: Players DataFrame.

        Returns:
            pd.DataFrame indexed by position with summary columns.
        """
        cols = ["player_count", "total_points", "average_points", "average_price"]
        if df.empty:
            return pd.DataFrame(columns=cols)

        grouped = df.groupby("position").agg(
            player_count=("id", "count"),
            total_points=("total_points", "sum"),
            average_points=("total_points", "mean"),
            average_price=("price", "mean"),
        )
        grouped["average_points"] = grouped["average_points"].round(2)
        grouped["average_price"] = grouped["average_price"].round(2)
        return grouped.sort_values(by="total_points", ascending=False)

    def get_team_distribution(self, df: pd.DataFrame) -> dict[str, int]:
        """Compute counts of players by team.

        Args:
            df: Players DataFrame.

        Returns:
            Dict mapping team code to count.
        """
        if df.empty:
            return {}
        counts = df["team"].value_counts().sort_index()
        return {str(team): int(cnt) for team, cnt in counts.items()}

    def get_team_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute aggregated metrics by team: total points, average price, player count.

        Args:
            df: Players DataFrame.

        Returns:
            pd.DataFrame indexed by team with summary columns.
        """
        cols = ["total_points", "average_price", "player_count"]
        if df.empty:
            return pd.DataFrame(columns=cols)

        grouped = df.groupby("team").agg(
            total_points=("total_points", "sum"),
            average_price=("price", "mean"),
            player_count=("id", "count"),
        )
        grouped["average_price"] = grouped["average_price"].round(2)
        return grouped.sort_values(by="total_points", ascending=False)

    def get_points_by_position(self, df: pd.DataFrame) -> dict[str, int]:
        """Compute aggregate total points accumulated by position.

        Args:
            df: Players DataFrame.

        Returns:
            Dict mapping position code to accumulated points.
        """
        if df.empty:
            return {}
        totals = df.groupby("position")["total_points"].sum().sort_values(ascending=False)
        return {str(pos): int(pts) for pos, pts in totals.items()}

    def get_quality_report(self, df: pd.DataFrame) -> FPLQualityReport:
        """Run technical data quality audit over the FPL dataset.

        Args:
            df: Players DataFrame.

        Returns:
            FPLQualityReport dataclass.
        """
        if df.empty:
            return FPLQualityReport(
                total_records=0,
                missing_prices=0,
                missing_teams=0,
                missing_positions=0,
                duplicate_ids=0,
                is_empty=True,
            )

        total_records = len(df)
        missing_prices = int(df["price"].isna().sum())
        missing_teams = int((df["team"].isna() | (df["team"].astype(str).str.strip() == "")).sum())
        missing_pos = int((df["position"].isna() | (df["position"].astype(str).str.strip() == "")).sum())
        duplicate_ids = int(df["id"].duplicated().sum())

        return FPLQualityReport(
            total_records=total_records,
            missing_prices=missing_prices,
            missing_teams=missing_teams,
            missing_positions=missing_pos,
            duplicate_ids=duplicate_ids,
            is_empty=False,
        )

    def analyze(self) -> FPLAnalyticsResult:
        """Execute full analytical aggregations and produce FPLAnalyticsResult bundle.

        Returns:
            FPLAnalyticsResult dataclass.
        """
        df = self.load_data()
        return FPLAnalyticsResult(
            summary=self.get_summary_statistics(df),
            quality=self.get_quality_report(df),
            top_points=self.get_top_by_column(df, "total_points", n=5),
            top_value=self.get_top_by_column(df, "points_per_million", n=5),
            top_form=self.get_top_by_column(df, "form", n=5),
            top_selected=self.get_top_by_column(df, "selected_by_percent", n=5),
            top_goalscorers=self.get_top_by_column(df, "goals", n=5),
            top_assists=self.get_top_by_column(df, "assists", n=5),
            position_distribution=self.get_position_distribution(df),
            team_distribution=self.get_team_distribution(df),
            points_by_position=self.get_points_by_position(df),
        )


def run_fpl_analytics_cli() -> None:
    """CLI runner for FPL analytics."""
    parser = argparse.ArgumentParser(description="Analyze FPL player data stored in SQLite database.")
    parser.add_argument(
        "--db-path",
        default="data/processed/fpl.db",
        help="Path to SQLite database (default: data/processed/fpl.db)",
    )
    args = parser.parse_args()

    analytics = FPLAnalytics(db_path=args.db_path)
    result = analytics.analyze()
    summary = result.summary
    quality = result.quality

    print("\n" + "=" * 65)
    print("Fantasy Premier League (FPL) Analytics & Business Intelligence")
    print("=" * 65)
    print(f"Database:              {args.db_path}")
    print(f"Total Players:         {summary.total_players}")
    print(f"Average Price:         £{summary.average_price:.2f}m" if summary.average_price is not None else "Average Price:         N/A")
    print(f"Median Price:          £{summary.median_price:.2f}m" if summary.median_price is not None else "Median Price:          N/A")
    print(f"Price Range:           £{summary.min_price:.2f}m - £{summary.max_price:.2f}m" if summary.min_price is not None else "Price Range:           N/A")
    print(f"Total Goals Scored:    {summary.total_goals_scored}")
    print(f"Total Assists Made:    {summary.total_assists_provided}")
    print(f"Average Total Points:  {summary.average_points:.1f}" if summary.average_points is not None else "Average Total Points:  N/A")
    print("=" * 65)

    print("\nTop 5 Total Points Leaders:")
    if result.top_points:
        for idx, p in enumerate(result.top_points, start=1):
            print(f"  [{idx}] {p['web_name']} ({p['team']}, {p['position']}) -- {p['total_points']} pts | £{p['price']:.1f}m")
    else:
        print("  (No player records)")

    print("\nTop 5 Value Leaders (Points Per Million):")
    if result.top_value:
        for idx, p in enumerate(result.top_value, start=1):
            print(f"  [{idx}] {p['web_name']} ({p['team']}) -- {p['points_per_million']} pts/£m ({p['total_points']} pts @ £{p['price']:.1f}m)")
    else:
        print("  (No player records)")

    print("\nTop 5 Form Leaders (Pts / Match Recent):")
    if result.top_form:
        for idx, p in enumerate(result.top_form, start=1):
            print(f"  [{idx}] {p['web_name']} ({p['team']}) -- Form: {p['form']} ({p['total_points']} pts)")
    else:
        print("  (No player records)")

    print("\nPosition Breakdown:")
    if result.position_distribution:
        for pos, cnt in result.position_distribution.items():
            pts = result.points_by_position.get(pos, 0)
            print(f"  {pos:4s}: {cnt:3d} players | {pts:5d} total points")
    else:
        print("  (No position distribution data)")

    print("\nData Quality Audit:")
    print(f"  Missing Prices:       {quality.missing_prices}")
    print(f"  Missing Teams:        {quality.missing_teams}")
    print(f"  Missing Positions:    {quality.missing_positions}")
    print(f"  Duplicate Player IDs: {quality.duplicate_ids}")
    print(f"  Dataset Status:       {'EMPTY' if quality.is_empty else 'HEALTHY'}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    from pathlib import Path
    import sys

    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    run_fpl_analytics_cli()
