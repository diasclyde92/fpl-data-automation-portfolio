"""Historical analytics layer for comparing FPL snapshots across pipeline runs and tracking trends."""

import argparse
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.storage.fpl_storage import FPLStorage

logger = logging.getLogger(__name__)

SNAPSHOT_NUMERIC_INT_COLS = [
    "player_id",
    "total_points",
    "event_points",
    "goals",
    "assists",
    "clean_sheets",
    "minutes",
    "bonus",
]

SNAPSHOT_NUMERIC_FLOAT_COLS = [
    "price",
    "selected_by_percent",
    "form",
]


@dataclass(frozen=True)
class HistoricalSummaryStats:
    """Summary metrics comparing two pipeline runs."""

    latest_run_id: str | None
    previous_run_id: str | None
    latest_scraped_at: datetime | None
    previous_scraped_at: datetime | None
    total_players_compared: int
    players_with_price_changes: int
    players_with_ownership_changes: int
    players_with_points_changes: int


@dataclass(frozen=True)
class HistoricalQualityReport:
    """Integrity audit across runs and snapshots."""

    total_runs: int
    total_snapshots: int
    duplicate_snapshots: int
    orphan_snapshots: int
    missing_runs: int
    status: str  # "healthy history", "limited history", "empty history", "integrity issue"
    details: list[str]


@dataclass(frozen=True)
class HistoricalAnalyticsResult:
    """Structured analytical bundle returned by FPLHistoricalAnalytics."""

    summary: HistoricalSummaryStats
    quality: HistoricalQualityReport
    price_increases: list[dict[str, Any]]
    price_decreases: list[dict[str, Any]]
    ownership_gainers: list[dict[str, Any]]
    ownership_losers: list[dict[str, Any]]
    points_gainers: list[dict[str, Any]]
    form_risers: list[dict[str, Any]]
    form_fallers: list[dict[str, Any]]
    value_improvers: list[dict[str, Any]]
    value_decliners: list[dict[str, Any]]
    rising_players: list[dict[str, Any]]
    falling_players: list[dict[str, Any]]
    team_comparison: list[dict[str, Any]]
    position_comparison: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        return asdict(self)


class FPLHistoricalAnalytics:
    """Analyzes historical snapshots from FPLStorage to compute price, ownership, form, and value trends."""

    def __init__(
        self,
        storage: FPLStorage | None = None,
        db_path: Path | str = "data/processed/fpl.db",
    ) -> None:
        """Initialize historical analytics with storage engine or db path.

        Args:
            storage: Optional FPLStorage instance.
            db_path: Path to SQLite database if storage is omitted.
        """
        self.storage = storage or FPLStorage(db_path=db_path)

    def load_runs(self) -> pd.DataFrame:
        """Load fpl_runs records into a typed DataFrame sorted chronologically.

        Returns:
            pd.DataFrame with UTC scraped_at and normalized types.
        """
        runs = self.storage.get_run_history(limit=500)
        if not runs:
            return pd.DataFrame(
                columns=[
                    "run_id",
                    "scraped_at",
                    "source",
                    "records_extracted",
                    "records_valid",
                    "records_invalid",
                    "records_persisted",
                    "status",
                    "duration_seconds",
                    "error_message",
                ]
            )

        df = pd.DataFrame(runs)
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True, errors="coerce")
        df["records_extracted"] = pd.to_numeric(df["records_extracted"], errors="coerce").fillna(0).astype("int64")
        df["records_valid"] = pd.to_numeric(df["records_valid"], errors="coerce").fillna(0).astype("int64")
        df["records_persisted"] = pd.to_numeric(df["records_persisted"], errors="coerce").fillna(0).astype("int64")
        # Sort chronologically ascending
        df = df.sort_values(by="scraped_at", ascending=True).reset_index(drop=True)
        return df

    def load_snapshots(self, run_id: str | None = None) -> pd.DataFrame:
        """Load player snapshots into a typed DataFrame with computed value metrics.

        Args:
            run_id: Optional specific run_id to filter snapshots.

        Returns:
            pd.DataFrame of player snapshots.
        """
        if run_id:
            records = self.storage.get_snapshot(run_id=run_id)
        else:
            records = self.storage.get_all_snapshots()

        if not records:
            return pd.DataFrame(
                columns=[
                    "run_id",
                    "player_id",
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
                    "points_per_million",
                ]
            )

        df = pd.DataFrame(records)

        # Type coercion
        for col in SNAPSHOT_NUMERIC_INT_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int64")

        for col in SNAPSHOT_NUMERIC_FLOAT_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype("float64")

        df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True, errors="coerce")

        # Computed points_per_million
        df["points_per_million"] = (
            df["total_points"] / df["price"].replace(0, pd.NA)
        ).round(2).fillna(0.0).astype("float64")

        return df

    def get_latest_runs(self) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Identify the latest and immediately preceding completed runs.

        Returns:
            Tuple of (latest_run_dict, previous_run_dict).
        """
        runs_df = self.load_runs()
        if runs_df.empty:
            return None, None

        # Filter completed runs (completed or completed_with_errors)
        valid_runs = runs_df[runs_df["status"].isin(["completed", "completed_with_errors"])]
        if valid_runs.empty:
            valid_runs = runs_df  # Fallback to any runs if none flagged completed

        if len(valid_runs) == 1:
            return valid_runs.iloc[-1].to_dict(), None

        latest = valid_runs.iloc[-1].to_dict()
        previous = valid_runs.iloc[-2].to_dict()
        return latest, previous

    def compare_runs(
        self,
        latest_run_id: str,
        previous_run_id: str,
    ) -> pd.DataFrame:
        """Compare two specific runs and compute player-level delta metrics.

        Delta calculation is explicitly defined as:
            latest_run_value - previous_run_value

        Args:
            latest_run_id: Identifier for the more recent run.
            previous_run_id: Identifier for the earlier run.

        Returns:
            pd.DataFrame with previous, latest, and change columns per player.
        """
        df_prev = self.load_snapshots(run_id=previous_run_id)
        df_curr = self.load_snapshots(run_id=latest_run_id)

        if df_prev.empty or df_curr.empty:
            return pd.DataFrame()

        # Merge on player_id
        merged = pd.merge(
            df_prev,
            df_curr,
            on="player_id",
            suffixes=("_prev", "_latest"),
            how="inner",
        )

        if merged.empty:
            return pd.DataFrame()

        # Retain static player attributes from latest run
        merged["web_name"] = merged["web_name_latest"]
        merged["team"] = merged["team_latest"]
        merged["position"] = merged["position_latest"]

        # Delta calculations: latest - previous
        merged["price_change"] = (merged["price_latest"] - merged["price_prev"]).round(2)
        merged["total_points_change"] = (merged["total_points_latest"] - merged["total_points_prev"]).astype("int64")
        merged["event_points_change"] = (merged["event_points_latest"] - merged["event_points_prev"]).astype("int64")
        # Ownership change in absolute percentage points (e.g. 4.0 - 2.5 = +1.5 pp)
        merged["ownership_change_pp"] = (merged["selected_by_percent_latest"] - merged["selected_by_percent_prev"]).round(2)
        merged["form_change"] = (merged["form_latest"] - merged["form_prev"]).round(2)
        merged["goals_change"] = (merged["goals_latest"] - merged["goals_prev"]).astype("int64")
        merged["assists_change"] = (merged["assists_latest"] - merged["assists_prev"]).astype("int64")
        merged["clean_sheets_change"] = (merged["clean_sheets_latest"] - merged["clean_sheets_prev"]).astype("int64")
        merged["minutes_change"] = (merged["minutes_latest"] - merged["minutes_prev"]).astype("int64")
        merged["bonus_change"] = (merged["bonus_latest"] - merged["bonus_prev"]).astype("int64")
        merged["value_change"] = (merged["points_per_million_latest"] - merged["points_per_million_prev"]).round(2)

        return merged

    def get_price_movers(
        self,
        diff_df: pd.DataFrame,
        top_n: int = 10,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Extract top price increases and top price decreases.

        Args:
            diff_df: DataFrame returned by compare_runs.
            top_n: Number of records to return.

        Returns:
            Tuple of (price_increases_df, price_decreases_df).
        """
        cols = [
            "player_id",
            "web_name",
            "team",
            "position",
            "price_prev",
            "price_latest",
            "price_change",
        ]
        if diff_df.empty or "price_change" not in diff_df.columns:
            empty = pd.DataFrame(columns=cols)
            return empty, empty

        inc = diff_df[diff_df["price_change"] > 0].sort_values(by="price_change", ascending=False).head(top_n)[cols]
        dec = diff_df[diff_df["price_change"] < 0].sort_values(by="price_change", ascending=True).head(top_n)[cols]

        return inc.reset_index(drop=True), dec.reset_index(drop=True)

    def get_ownership_movers(
        self,
        diff_df: pd.DataFrame,
        top_n: int = 10,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Extract top ownership increases and decreases in percentage points.

        Args:
            diff_df: DataFrame returned by compare_runs.
            top_n: Number of records to return.

        Returns:
            Tuple of (ownership_gainers_df, ownership_losers_df).
        """
        cols = [
            "player_id",
            "web_name",
            "team",
            "position",
            "selected_by_percent_prev",
            "selected_by_percent_latest",
            "ownership_change_pp",
        ]
        if diff_df.empty or "ownership_change_pp" not in diff_df.columns:
            empty = pd.DataFrame(columns=cols)
            return empty, empty

        gainers = diff_df.sort_values(by="ownership_change_pp", ascending=False).head(top_n)[cols]
        losers = diff_df.sort_values(by="ownership_change_pp", ascending=True).head(top_n)[cols]

        return gainers.reset_index(drop=True), losers.reset_index(drop=True)

    def get_performance_movers(
        self,
        diff_df: pd.DataFrame,
        top_n: int = 10,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Extract total points gainers, form risers, and form fallers.

        Args:
            diff_df: DataFrame returned by compare_runs.
            top_n: Number of records to return.

        Returns:
            Tuple of (points_gainers, form_risers, form_fallers).
        """
        pts_cols = [
            "player_id",
            "web_name",
            "team",
            "position",
            "total_points_prev",
            "total_points_latest",
            "total_points_change",
            "event_points_latest",
        ]
        form_cols = [
            "player_id",
            "web_name",
            "team",
            "position",
            "form_prev",
            "form_latest",
            "form_change",
        ]

        if diff_df.empty:
            return pd.DataFrame(columns=pts_cols), pd.DataFrame(columns=form_cols), pd.DataFrame(columns=form_cols)

        pts_gainers = diff_df.sort_values(by="total_points_change", ascending=False).head(top_n)[pts_cols]
        form_risers = diff_df.sort_values(by="form_change", ascending=False).head(top_n)[form_cols]
        form_fallers = diff_df.sort_values(by="form_change", ascending=True).head(top_n)[form_cols]

        return pts_gainers.reset_index(drop=True), form_risers.reset_index(drop=True), form_fallers.reset_index(drop=True)

    def get_value_movers(
        self,
        diff_df: pd.DataFrame,
        top_n: int = 10,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Extract value (points per million) improvers and decliners.

        Args:
            diff_df: DataFrame returned by compare_runs.
            top_n: Number of records to return.

        Returns:
            Tuple of (value_improvers, value_decliners).
        """
        cols = [
            "player_id",
            "web_name",
            "team",
            "position",
            "points_per_million_prev",
            "points_per_million_latest",
            "value_change",
        ]
        if diff_df.empty or "value_change" not in diff_df.columns:
            empty = pd.DataFrame(columns=cols)
            return empty, empty

        improvers = diff_df.sort_values(by="value_change", ascending=False).head(top_n)[cols]
        decliners = diff_df.sort_values(by="value_change", ascending=True).head(top_n)[cols]

        return improvers.reset_index(drop=True), decliners.reset_index(drop=True)

    def get_player_history(self, player_id: int) -> pd.DataFrame:
        """Retrieve chronological snapshot timeline for a specific player ID.

        Args:
            player_id: Integer player ID.

        Returns:
            pd.DataFrame sorted by scraped_at ASC with value efficiency metrics.
        """
        records = self.storage.get_player_history(player_id=player_id)
        if not records:
            return pd.DataFrame(
                columns=[
                    "run_id",
                    "player_id",
                    "web_name",
                    "team",
                    "position",
                    "price",
                    "total_points",
                    "event_points",
                    "selected_by_percent",
                    "form",
                    "goals",
                    "assists",
                    "minutes",
                    "bonus",
                    "points_per_million",
                    "scraped_at",
                ]
            )

        df = pd.DataFrame(records)
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True, errors="coerce")
        df["price"] = pd.to_numeric(df["price"], errors="coerce").astype("float64")
        df["total_points"] = pd.to_numeric(df["total_points"], errors="coerce").astype("int64")
        df["points_per_million"] = (
            df["total_points"] / df["price"].replace(0, pd.NA)
        ).round(2).fillna(0.0).astype("float64")

        return df.sort_values(by="scraped_at", ascending=True).reset_index(drop=True)

    def get_team_comparison(
        self,
        latest_run_id: str,
        previous_run_id: str,
    ) -> pd.DataFrame:
        """Aggregate and compare total points, average price, and player count by team across two runs.

        Args:
            latest_run_id: More recent run identifier.
            previous_run_id: Preceding run identifier.

        Returns:
            pd.DataFrame comparing team metrics between runs.
        """
        df_prev = self.load_snapshots(run_id=previous_run_id)
        df_curr = self.load_snapshots(run_id=latest_run_id)

        cols = ["team", "total_points_prev", "total_points_latest", "points_change", "avg_price_prev", "avg_price_latest", "player_count"]
        if df_prev.empty or df_curr.empty:
            return pd.DataFrame(columns=cols)

        agg_prev = df_prev.groupby("team").agg(
            total_points_prev=("total_points", "sum"),
            avg_price_prev=("price", "mean"),
        )
        agg_curr = df_curr.groupby("team").agg(
            total_points_latest=("total_points", "sum"),
            avg_price_latest=("price", "mean"),
            player_count=("player_id", "count"),
        )

        merged = pd.merge(agg_prev, agg_curr, on="team", how="outer").fillna(0)
        merged["points_change"] = merged["total_points_latest"] - merged["total_points_prev"]
        merged["avg_price_prev"] = merged["avg_price_prev"].round(2)
        merged["avg_price_latest"] = merged["avg_price_latest"].round(2)
        merged = merged.reset_index()

        return merged.sort_values(by="total_points_latest", ascending=False).reset_index(drop=True)

    def get_position_comparison(
        self,
        latest_run_id: str,
        previous_run_id: str,
    ) -> pd.DataFrame:
        """Aggregate and compare points and average prices by position across two runs.

        Args:
            latest_run_id: More recent run identifier.
            previous_run_id: Preceding run identifier.

        Returns:
            pd.DataFrame comparing position metrics between runs.
        """
        df_prev = self.load_snapshots(run_id=previous_run_id)
        df_curr = self.load_snapshots(run_id=latest_run_id)

        cols = ["position", "total_points_prev", "total_points_latest", "points_change", "avg_price_prev", "avg_price_latest", "player_count"]
        if df_prev.empty or df_curr.empty:
            return pd.DataFrame(columns=cols)

        agg_prev = df_prev.groupby("position").agg(
            total_points_prev=("total_points", "sum"),
            avg_price_prev=("price", "mean"),
        )
        agg_curr = df_curr.groupby("position").agg(
            total_points_latest=("total_points", "sum"),
            avg_price_latest=("price", "mean"),
            player_count=("player_id", "count"),
        )

        merged = pd.merge(agg_prev, agg_curr, on="position", how="outer").fillna(0)
        merged["points_change"] = merged["total_points_latest"] - merged["total_points_prev"]
        merged["avg_price_prev"] = merged["avg_price_prev"].round(2)
        merged["avg_price_latest"] = merged["avg_price_latest"].round(2)
        merged = merged.reset_index()

        return merged.sort_values(by="total_points_latest", ascending=False).reset_index(drop=True)

    def get_rising_and_falling_players(
        self,
        diff_df: pd.DataFrame,
        top_n: int = 10,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Derive transparent momentum rankings for rising and falling players.

        Methodology:
        - Rising Score: (ownership_change_pp * 2.0) + (form_change * 1.0) + (value_change * 0.5)
        - Falling Score: same transparent linear formula sorted ascending.
        Scores are purely transparent weighted aggregates of verified delta metrics.

        Args:
            diff_df: DataFrame returned by compare_runs.
            top_n: Number of records to return.

        Returns:
            Tuple of (rising_players_df, falling_players_df).
        """
        cols = [
            "player_id",
            "web_name",
            "team",
            "position",
            "ownership_change_pp",
            "form_change",
            "value_change",
            "momentum_score",
        ]
        if diff_df.empty or "ownership_change_pp" not in diff_df.columns:
            empty = pd.DataFrame(columns=cols)
            return empty, empty

        calc_df = diff_df.copy()
        calc_df["momentum_score"] = (
            (calc_df["ownership_change_pp"] * 2.0)
            + (calc_df["form_change"] * 1.0)
            + (calc_df["value_change"] * 0.5)
        ).round(2)

        rising = calc_df.sort_values(by="momentum_score", ascending=False).head(top_n)[cols]
        falling = calc_df.sort_values(by="momentum_score", ascending=True).head(top_n)[cols]

        return rising.reset_index(drop=True), falling.reset_index(drop=True)

    def get_historical_quality_report(self) -> HistoricalQualityReport:
        """Run technical health and data integrity check on the historical storage layer.

        Returns:
            HistoricalQualityReport dataclass.
        """
        runs_df = self.load_runs()
        total_runs = len(runs_df)
        total_snapshots = self.storage.count_snapshots()

        details = []

        if total_runs == 0:
            return HistoricalQualityReport(
                total_runs=0,
                total_snapshots=0,
                duplicate_snapshots=0,
                orphan_snapshots=0,
                missing_runs=0,
                status="empty history",
                details=["No pipeline runs found in database."],
            )

        # Check for orphan snapshots
        all_snapshots = self.load_snapshots()
        orphan_snapshots = 0
        duplicate_snapshots = 0
        if not all_snapshots.empty and not runs_df.empty:
            valid_run_ids = set(runs_df["run_id"])
            snapshot_run_ids = set(all_snapshots["run_id"])
            orphans = snapshot_run_ids - valid_run_ids
            orphan_snapshots = len(all_snapshots[all_snapshots["run_id"].isin(orphans)])
            # Duplicate (run_id, player_id) check
            duplicate_snapshots = int(all_snapshots.duplicated(subset=["run_id", "player_id"]).sum())

        missing_runs = int(runs_df["status"].isin(["failed", "started"]).sum())

        if orphan_snapshots > 0 or duplicate_snapshots > 0:
            status = "integrity issue"
            if duplicate_snapshots > 0:
                details.append(f"Found {duplicate_snapshots} duplicate (run_id, player_id) rows.")
            if orphan_snapshots > 0:
                details.append(f"Found {orphan_snapshots} snapshots referencing missing runs.")
        elif total_runs < 2:
            status = "limited history"
            details.append("Only one run exists. Historical comparison requires at least 2 runs.")
        else:
            status = "healthy history"
            details.append(f"Repository contains {total_runs} runs and {total_snapshots} immutable snapshots.")

        return HistoricalQualityReport(
            total_runs=total_runs,
            total_snapshots=total_snapshots,
            duplicate_snapshots=duplicate_snapshots,
            orphan_snapshots=orphan_snapshots,
            missing_runs=missing_runs,
            status=status,
            details=details,
        )

    def analyze(
        self,
        latest_run_id: str | None = None,
        previous_run_id: str | None = None,
        top_n: int = 10,
    ) -> HistoricalAnalyticsResult:
        """Execute full historical analysis and compile HistoricalAnalyticsResult.

        If run IDs are omitted, automatically selects latest and previous completed runs.

        Args:
            latest_run_id: Optional latest run ID.
            previous_run_id: Optional previous run ID.
            top_n: Number of leaderboard items to extract.

        Returns:
            HistoricalAnalyticsResult dataclass.
        """
        quality = self.get_historical_quality_report()

        # Resolve runs
        if not latest_run_id or not previous_run_id:
            latest_dict, prev_dict = self.get_latest_runs()
            if latest_dict:
                latest_run_id = latest_dict["run_id"]
            if prev_dict:
                previous_run_id = prev_dict["run_id"]

        # Handle zero or single run edge case
        if not latest_run_id or not previous_run_id:
            summary = HistoricalSummaryStats(
                latest_run_id=latest_run_id,
                previous_run_id=None,
                latest_scraped_at=None,
                previous_scraped_at=None,
                total_players_compared=0,
                players_with_price_changes=0,
                players_with_ownership_changes=0,
                players_with_points_changes=0,
            )
            return HistoricalAnalyticsResult(
                summary=summary,
                quality=quality,
                price_increases=[],
                price_decreases=[],
                ownership_gainers=[],
                ownership_losers=[],
                points_gainers=[],
                form_risers=[],
                form_fallers=[],
                value_improvers=[],
                value_decliners=[],
                rising_players=[],
                falling_players=[],
                team_comparison=[],
                position_comparison=[],
            )

        # Execute comparison
        diff_df = self.compare_runs(latest_run_id=latest_run_id, previous_run_id=previous_run_id)

        # Calculate movers
        price_inc, price_dec = self.get_price_movers(diff_df, top_n=top_n)
        own_gain, own_lose = self.get_ownership_movers(diff_df, top_n=top_n)
        pts_gain, form_rise, form_fall = self.get_performance_movers(diff_df, top_n=top_n)
        val_imp, val_dec = self.get_value_movers(diff_df, top_n=top_n)
        rising, falling = self.get_rising_and_falling_players(diff_df, top_n=top_n)
        team_comp = self.get_team_comparison(latest_run_id, previous_run_id)
        pos_comp = self.get_position_comparison(latest_run_id, previous_run_id)

        # Summary statistics
        runs_df = self.load_runs()
        lat_row = runs_df[runs_df["run_id"] == latest_run_id]
        prev_row = runs_df[runs_df["run_id"] == previous_run_id]
        lat_ts = lat_row.iloc[0]["scraped_at"] if not lat_row.empty else None
        prev_ts = prev_row.iloc[0]["scraped_at"] if not prev_row.empty else None

        summary = HistoricalSummaryStats(
            latest_run_id=latest_run_id,
            previous_run_id=previous_run_id,
            latest_scraped_at=lat_ts,
            previous_scraped_at=prev_ts,
            total_players_compared=len(diff_df),
            players_with_price_changes=int((diff_df["price_change"] != 0).sum()) if not diff_df.empty else 0,
            players_with_ownership_changes=int((diff_df["ownership_change_pp"] != 0).sum()) if not diff_df.empty else 0,
            players_with_points_changes=int((diff_df["total_points_change"] != 0).sum()) if not diff_df.empty else 0,
        )

        return HistoricalAnalyticsResult(
            summary=summary,
            quality=quality,
            price_increases=price_inc.to_dict(orient="records"),
            price_decreases=price_dec.to_dict(orient="records"),
            ownership_gainers=own_gain.to_dict(orient="records"),
            ownership_losers=own_lose.to_dict(orient="records"),
            points_gainers=pts_gain.to_dict(orient="records"),
            form_risers=form_rise.to_dict(orient="records"),
            form_fallers=form_fall.to_dict(orient="records"),
            value_improvers=val_imp.to_dict(orient="records"),
            value_decliners=val_dec.to_dict(orient="records"),
            rising_players=rising.to_dict(orient="records"),
            falling_players=falling.to_dict(orient="records"),
            team_comparison=team_comp.to_dict(orient="records"),
            position_comparison=pos_comp.to_dict(orient="records"),
        )


def run_historical_analytics_cli() -> None:
    """CLI runner for FPL Historical Analytics."""
    parser = argparse.ArgumentParser(description="Analyze FPL historical trends across snapshot runs.")
    parser.add_argument("--db-path", default="data/processed/fpl.db", help="Path to SQLite database")
    parser.add_argument("--latest-run", default=None, help="Latest run ID to compare")
    parser.add_argument("--previous-run", default=None, help="Previous run ID to compare")
    parser.add_argument("--top-n", type=int, default=5, help="Number of records to display in tables")
    parser.add_argument("--player-id", type=int, default=None, help="Inspect historical trend for specific player ID")
    args = parser.parse_args()

    analytics = FPLHistoricalAnalytics(db_path=args.db_path)

    # Individual Player History Mode
    if args.player_id:
        p_history = analytics.get_player_history(player_id=args.player_id)
        print("\n" + "=" * 65)
        print(f"FPL Player Historical Snapshot Timeline: #{args.player_id}")
        print("=" * 65)
        if p_history.empty:
            print(f"No history found for player ID #{args.player_id}")
        else:
            p_name = p_history.iloc[0]["web_name"]
            team = p_history.iloc[0]["team"]
            pos = p_history.iloc[0]["position"]
            print(f"Player: {p_name} ({team} - {pos}) | Total Snapshots: {len(p_history)}\n")
            cols = ["run_id", "scraped_at", "price", "total_points", "event_points", "selected_by_percent", "form", "points_per_million"]
            print(p_history[cols].to_string(index=False))
        print("=" * 65 + "\n")
        return

    # Run Comparison Mode
    res = analytics.analyze(latest_run_id=args.latest_run, previous_run_id=args.previous_run, top_n=args.top_n)
    summary = res.summary
    quality = res.quality

    print("\n" + "=" * 65)
    print("Fantasy Premier League (FPL) Historical Analytics & Trend Analysis")
    print("=" * 65)
    print(f"Database:             {args.db_path}")
    print(f"Historical Status:    {quality.status.upper()}")
    print(f"Total Stored Runs:    {quality.total_runs}")
    print(f"Total Snapshots:      {quality.total_snapshots}")
    print(f"Latest Run:           {summary.latest_run_id or 'N/A'}")
    print(f"Previous Run:         {summary.previous_run_id or 'N/A'}")
    print(f"Players Compared:     {summary.total_players_compared}")
    print("=" * 65)

    if quality.status in ["empty history", "limited history"] or not summary.previous_run_id:
        print("\n⚠️  Historical comparison unavailable.")
        for detail in quality.details:
            print(f"   - {detail}")
        print("\n" + "=" * 65 + "\n")
        return

    # Top Price Movers
    print(f"\nTop Price Increases (Top {args.top_n}):")
    if res.price_increases:
        for idx, p in enumerate(res.price_increases, 1):
            print(f"  [{idx}] {p['web_name']:12s} ({p['team']}) -- £{p['price_prev']:.1f}m -> £{p['price_latest']:.1f}m (+£{p['price_change']:.1f}m)")
    else:
        print("  (No price increases between runs)")

    print(f"\nTop Ownership Gainers (Percentage Points, Top {args.top_n}):")
    if res.ownership_gainers:
        for idx, p in enumerate(res.ownership_gainers, 1):
            print(f"  [{idx}] {p['web_name']:12s} ({p['team']}) -- {p['selected_by_percent_prev']:.1f}% -> {p['selected_by_percent_latest']:.1f}% ({p['ownership_change_pp']:+.2f} pp)")
    else:
        print("  (No ownership gainers)")

    print(f"\nTop Form Risers (Top {args.top_n}):")
    if res.form_risers:
        for idx, p in enumerate(res.form_risers, 1):
            print(f"  [{idx}] {p['web_name']:12s} ({p['team']}) -- Form: {p['form_prev']:.1f} -> {p['form_latest']:.1f} ({p['form_change']:+.1f})")
    else:
        print("  (No form risers)")

    print(f"\nTop Value Improvers (PPM, Top {args.top_n}):")
    if res.value_improvers:
        for idx, p in enumerate(res.value_improvers, 1):
            print(f"  [{idx}] {p['web_name']:12s} ({p['team']}) -- PPM: {p['points_per_million_prev']:.2f} -> {p['points_per_million_latest']:.2f} ({p['value_change']:+.2f})")
    else:
        print("  (No value improvers)")

    print(f"\nTop Rising Players (Momentum Ranking, Top {args.top_n}):")
    if res.rising_players:
        for idx, p in enumerate(res.rising_players, 1):
            print(f"  [{idx}] {p['web_name']:12s} ({p['team']}) -- Momentum Score: {p['momentum_score']:+.2f} (Own: {p['ownership_change_pp']:+.1f}pp, Form: {p['form_change']:+.1f})")
    else:
        print("  (No rising players)")

    print("=" * 65 + "\n")


if __name__ == "__main__":
    from pathlib import Path
    import sys

    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    run_historical_analytics_cli()
