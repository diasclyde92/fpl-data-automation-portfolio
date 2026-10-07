"""Tests for FPL Dashboard service helper functions and business logic."""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.dashboard.fpl_dashboard_service import (
    DashboardFilterCriteria,
    filter_players_dataframe,
    get_fpl_analytics_bundle,
    get_player_card_details,
)
from src.models.fpl_player import FPLPlayer
from src.storage.fpl_storage import FPLStorage


@pytest.fixture
def sample_dashboard_df() -> pd.DataFrame:
    """Fixture returning sample players DataFrame with computed metrics."""
    return pd.DataFrame([
        {
            "id": 1,
            "first_name": "Bukayo",
            "second_name": "Saka",
            "web_name": "Saka",
            "team": "ARS",
            "position": "MID",
            "price": 10.0,
            "total_points": 85,
            "event_points": 8,
            "selected_by_percent": 35.0,
            "goals": 6,
            "assists": 7,
            "clean_sheets": 4,
            "minutes": 900,
            "bonus": 12,
            "form": 7.0,
            "status": "a",
            "points_per_million": 8.5,
            "points_per_90": 8.5,
            "scraped_at": datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc),
        },
        {
            "id": 2,
            "first_name": "Erling",
            "second_name": "Haaland",
            "web_name": "Haaland",
            "team": "MCI",
            "position": "FWD",
            "price": 15.0,
            "total_points": 120,
            "event_points": 13,
            "selected_by_percent": 70.0,
            "goals": 14,
            "assists": 3,
            "clean_sheets": 0,
            "minutes": 900,
            "bonus": 18,
            "form": 9.5,
            "status": "a",
            "points_per_million": 8.0,
            "points_per_90": 12.0,
            "scraped_at": datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc),
        },
        {
            "id": 3,
            "first_name": "David",
            "second_name": "Raya",
            "web_name": "Raya",
            "team": "ARS",
            "position": "GKP",
            "price": 5.0,
            "total_points": 40,
            "event_points": 6,
            "selected_by_percent": 25.0,
            "goals": 0,
            "assists": 0,
            "clean_sheets": 5,
            "minutes": 900,
            "bonus": 5,
            "form": 4.0,
            "status": "a",
            "points_per_million": 8.0,
            "points_per_90": 4.0,
            "scraped_at": datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc),
        },
        {
            "id": 4,
            "first_name": "Reece",
            "second_name": "James",
            "web_name": "James",
            "team": "CHE",
            "position": "DEF",
            "price": 5.5,
            "total_points": 15,
            "event_points": 0,
            "selected_by_percent": 5.0,
            "goals": 0,
            "assists": 1,
            "clean_sheets": 1,
            "minutes": 180,
            "bonus": 1,
            "form": 1.0,
            "status": "i",
            "points_per_million": 2.73,
            "points_per_90": 7.5,
            "scraped_at": datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc),
        },
    ])


def test_filter_players_dataframe_by_position(sample_dashboard_df: pd.DataFrame):
    """Verify filtering by position returns matching records."""
    criteria = DashboardFilterCriteria(positions=["MID", "FWD"])
    res = filter_players_dataframe(sample_dashboard_df, criteria)
    assert len(res) == 2
    assert set(res["position"]) == {"MID", "FWD"}


def test_filter_players_dataframe_by_team(sample_dashboard_df: pd.DataFrame):
    """Verify filtering by team returns players belonging only to those clubs."""
    criteria = DashboardFilterCriteria(teams=["ARS"])
    res = filter_players_dataframe(sample_dashboard_df, criteria)
    assert len(res) == 2
    assert set(res["web_name"]) == {"Saka", "Raya"}


def test_filter_players_dataframe_by_status_and_minutes(sample_dashboard_df: pd.DataFrame):
    """Verify filtering by availability status and minimum minutes."""
    criteria = DashboardFilterCriteria(statuses=["i"], min_minutes=100)
    res = filter_players_dataframe(sample_dashboard_df, criteria)
    assert len(res) == 1
    assert res.iloc[0]["web_name"] == "James"


def test_filter_players_dataframe_by_price_and_ownership(sample_dashboard_df: pd.DataFrame):
    """Verify filtering by price range and ownership threshold."""
    criteria = DashboardFilterCriteria(min_price=6.0, max_price=16.0, min_ownership=40.0)
    res = filter_players_dataframe(sample_dashboard_df, criteria)
    assert len(res) == 1
    assert res.iloc[0]["web_name"] == "Haaland"


def test_filter_players_dataframe_empty_input():
    """Verify filtering on empty DataFrame returns empty DataFrame safely."""
    empty_df = pd.DataFrame()
    criteria = DashboardFilterCriteria(positions=["MID"])
    res = filter_players_dataframe(empty_df, criteria)
    assert res.empty


def test_get_player_card_details_success(sample_dashboard_df: pd.DataFrame):
    """Verify retrieving player card details for valid ID."""
    details = get_player_card_details(sample_dashboard_df, player_id=2)
    assert details is not None
    assert details["web_name"] == "Haaland"
    assert details["team"] == "MCI"
    assert details["total_points"] == 120
    assert details["goals"] == 14


def test_get_player_card_details_nonexistent_or_empty(sample_dashboard_df: pd.DataFrame):
    """Verify retrieving details for nonexistent ID or empty DataFrame returns None."""
    assert get_player_card_details(sample_dashboard_df, player_id=999) is None
    assert get_player_card_details(pd.DataFrame(), player_id=1) is None


def test_get_fpl_analytics_bundle_with_data(tmp_path: Path):
    """Verify bundle loading from valid SQLite database."""
    db_file = tmp_path / "fpl_bundle_test.db"
    storage = FPLStorage(db_path=db_file)
    player = FPLPlayer(
        id=1, first_name="Son", second_name="Heung-min", web_name="Son", team="TOT", position="MID",
        price=9.5, total_points=70, event_points=6, selected_by_percent=20.0,
    )
    storage.insert_player(player)

    df, result, latest_scraped = get_fpl_analytics_bundle(db_path=db_file)
    assert len(df) == 1
    assert df.iloc[0]["web_name"] == "Son"
    assert result.summary.total_players == 1
    assert latest_scraped is not None


def test_get_fpl_analytics_bundle_nonexistent_db(tmp_path: Path):
    """Verify graceful handling when database file does not exist."""
    db_file = tmp_path / "does_not_exist.db"
    df, result, latest_scraped = get_fpl_analytics_bundle(db_path=db_file)
    assert df.empty
    assert result.summary.total_players == 0
    assert result.quality.is_empty is True
    assert latest_scraped is None


# ---------------------------------------------------------------------------
# Historical Dashboard Service Tests (Phase 13)
# ---------------------------------------------------------------------------

def test_get_fpl_historical_bundle_nonexistent_db(tmp_path: Path):
    """Verify historical bundle returns empty result safely when DB missing."""
    from src.dashboard.fpl_dashboard_service import get_fpl_historical_bundle
    bundle = get_fpl_historical_bundle(db_path=tmp_path / "nonexistent_fpl.db")
    assert isinstance(bundle, dict)
    assert bundle["quality"]["status"] == "empty history"
    assert bundle["summary"]["total_players_compared"] == 0


def test_get_fpl_historical_bundle_with_two_runs(tmp_path: Path):
    """Verify historical bundle loads comparison and movers properly."""
    from src.dashboard.fpl_dashboard_service import get_fpl_historical_bundle
    db_file = tmp_path / "fpl_bundle_hist.db"
    storage = FPLStorage(db_path=db_file)

    p1_r1 = FPLPlayer(
        id=1, first_name="A", second_name="B", web_name="P1", team="ARS", position="MID",
        price=10.0, total_points=50, event_points=5, selected_by_percent=20.0, form=5.0,
    )
    p1_r2 = FPLPlayer(
        id=1, first_name="A", second_name="B", web_name="P1", team="ARS", position="MID",
        price=10.2, total_points=60, event_points=10, selected_by_percent=25.0, form=7.0,
    )

    storage.create_run("run_1", source="http://test", scraped_at="2026-10-01T10:00:00+00:00")
    storage.save_current_and_snapshots("run_1", [p1_r1])
    storage.complete_run("run_1", 1, 1, 0, 1)

    storage.create_run("run_2", source="http://test", scraped_at="2026-10-02T10:00:00+00:00")
    storage.save_current_and_snapshots("run_2", [p1_r2])
    storage.complete_run("run_2", 1, 1, 0, 1)

    bundle = get_fpl_historical_bundle(db_path=db_file)
    assert bundle["quality"]["status"] == "healthy history"
    assert bundle["summary"]["total_players_compared"] == 1
    assert bundle["summary"]["latest_run_id"] == "run_2"
    assert bundle["summary"]["previous_run_id"] == "run_1"

    # Price rise
    assert len(bundle["price_increases"]) == 1
    assert bundle["price_increases"][0]["web_name"] == "P1"
    assert bundle["price_increases"][0]["price_change"] == 0.2

    # Ownership gain
    assert len(bundle["ownership_gainers"]) == 1
    assert bundle["ownership_gainers"][0]["ownership_change_pp"] == 5.0


def test_get_historical_player_timeline_service(tmp_path: Path):
    """Verify retrieving player timeline DataFrame via service layer."""
    from src.dashboard.fpl_dashboard_service import get_historical_player_timeline
    db_file = tmp_path / "fpl_timeline.db"
    storage = FPLStorage(db_path=db_file)

    p = FPLPlayer(
        id=42, first_name="Martin", second_name="Odegaard", web_name="Odegaard", team="ARS", position="MID",
        price=8.5, total_points=45, event_points=4, selected_by_percent=12.0,
    )
    storage.create_run("run_x", source="http://test", scraped_at="2026-10-01T10:00:00+00:00")
    storage.save_current_and_snapshots("run_x", [p])
    storage.complete_run("run_x", 1, 1, 0, 1)

    timeline = get_historical_player_timeline(player_id=42, db_path=db_file)
    assert len(timeline) == 1
    assert timeline.iloc[0]["web_name"] == "Odegaard"
    assert timeline.iloc[0]["price"] == 8.5
    assert timeline.iloc[0]["points_per_million"] == 5.29

    # Nonexistent player
    empty_tl = get_historical_player_timeline(player_id=999, db_path=db_file)
    assert empty_tl.empty

