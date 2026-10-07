"""Dashboard service helpers for data loading, filtering, and player selection."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.analytics.fpl_analytics import FPLAnalytics, FPLAnalyticsResult
from src.storage.fpl_storage import FPLStorage


@dataclass(frozen=True)
class DashboardFilterCriteria:
    """Filter criteria applied to player records in the dashboard."""

    positions: list[str] | None = None
    teams: list[str] | None = None
    statuses: list[str] | None = None
    min_price: float | None = None
    max_price: float | None = None
    min_ownership: float | None = None
    min_minutes: int | None = None


def get_fpl_analytics_bundle(
    db_path: Path | str = "data/processed/fpl.db",
) -> tuple[pd.DataFrame, FPLAnalyticsResult, datetime | None]:
    """Load FPL data, full analytics result, and latest scraped timestamp.

    Args:
        db_path: Path to FPL SQLite database.

    Returns:
        Tuple of (players_df, analytics_result, latest_scraped_at).
    """
    path_obj = Path(db_path)
    if not path_obj.exists():
        empty_analytics = FPLAnalytics(storage=None, db_path=path_obj)
        empty_df = empty_analytics.load_data()
        return empty_df, empty_analytics.analyze(), None

    storage = FPLStorage(db_path=path_obj)
    analytics = FPLAnalytics(storage=storage)
    df = analytics.load_data()
    result = analytics.analyze()

    latest_scraped_at: datetime | None = None
    if not df.empty and "scraped_at" in df.columns:
        valid_dates = df["scraped_at"].dropna()
        if not valid_dates.empty:
            latest_scraped_at = valid_dates.max()

    return df, result, latest_scraped_at


def filter_players_dataframe(
    df: pd.DataFrame,
    criteria: DashboardFilterCriteria,
) -> pd.DataFrame:
    """Apply interactive user filter criteria to players DataFrame.

    Keeps business logic pure and testable outside of Streamlit UI rendering.

    Args:
        df: Input players DataFrame.
        criteria: DashboardFilterCriteria instance.

    Returns:
        Filtered pd.DataFrame copy.
    """
    if df.empty:
        return df.copy()

    filtered = df.copy()

    if criteria.positions:
        filtered = filtered[filtered["position"].isin(criteria.positions)]

    if criteria.teams:
        filtered = filtered[filtered["team"].isin(criteria.teams)]

    if criteria.statuses:
        filtered = filtered[filtered["status"].isin(criteria.statuses)]

    if criteria.min_price is not None:
        filtered = filtered[filtered["price"] >= criteria.min_price]

    if criteria.max_price is not None:
        filtered = filtered[filtered["price"] <= criteria.max_price]

    if criteria.min_ownership is not None:
        filtered = filtered[filtered["selected_by_percent"] >= criteria.min_ownership]

    if criteria.min_minutes is not None:
        filtered = filtered[filtered["minutes"] >= criteria.min_minutes]

    return filtered


def get_player_card_details(df: pd.DataFrame, player_id: int) -> dict[str, Any] | None:
    """Retrieve full attribute dictionary for an individual selected player.

    Args:
        df: Players DataFrame.
        player_id: Integer player ID.

    Returns:
        Dictionary of player record details or None if not found.
    """
    if df.empty or "id" not in df.columns:
        return None

    matched = df[df["id"] == player_id]
    if matched.empty:
        return None

    return matched.iloc[0].to_dict()


def get_fpl_historical_bundle(
    db_path: Path | str = "data/processed/fpl.db",
    latest_run_id: str | None = None,
    previous_run_id: str | None = None,
    top_n: int = 10,
) -> dict[str, Any]:
    """Load historical runs, snapshot totals, and analytical trends.

    Args:
        db_path: Path to FPL SQLite database.
        latest_run_id: Optional latest run ID.
        previous_run_id: Optional previous run ID.
        top_n: Number of records to extract for trend tables.

    Returns:
        Dictionary representation of HistoricalAnalyticsResult.
    """
    from src.analytics.fpl_historical_analytics import FPLHistoricalAnalytics

    path_obj = Path(db_path)
    if not path_obj.exists():
        empty_hist = FPLHistoricalAnalytics(storage=None, db_path=path_obj)
        return empty_hist.analyze().to_dict()

    storage = FPLStorage(db_path=path_obj)
    hist_analytics = FPLHistoricalAnalytics(storage=storage)
    result = hist_analytics.analyze(
        latest_run_id=latest_run_id,
        previous_run_id=previous_run_id,
        top_n=top_n,
    )
    return result.to_dict()


def get_historical_player_timeline(
    player_id: int,
    db_path: Path | str = "data/processed/fpl.db",
) -> pd.DataFrame:
    """Retrieve individual player's chronological historical snapshots for charting.

    Args:
        player_id: Integer player ID.
        db_path: Path to FPL SQLite database.

    Returns:
        pd.DataFrame sorted chronologically by scraped_at.
    """
    from src.analytics.fpl_historical_analytics import FPLHistoricalAnalytics

    path_obj = Path(db_path)
    if not path_obj.exists():
        empty_hist = FPLHistoricalAnalytics(storage=None, db_path=path_obj)
        return empty_hist.get_player_history(player_id=player_id)

    storage = FPLStorage(db_path=path_obj)
    hist_analytics = FPLHistoricalAnalytics(storage=storage)
    return hist_analytics.get_player_history(player_id=player_id)

