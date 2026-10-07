"""Deterministic unit tests for FPL Historical Analytics layer (Phase 12)."""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.analytics.fpl_historical_analytics import FPLHistoricalAnalytics
from src.models.fpl_player import FPLPlayer
from src.storage.fpl_storage import FPLStorage


@pytest.fixture
def empty_storage(tmp_path: Path) -> FPLStorage:
    """Fixture providing empty FPLStorage."""
    return FPLStorage(db_path=tmp_path / "fpl_hist_empty.db")


@pytest.fixture
def one_run_storage(tmp_path: Path) -> FPLStorage:
    """Fixture providing storage with one completed run."""
    storage = FPLStorage(db_path=tmp_path / "fpl_hist_single.db")
    run_id = "fpl_20261001_100000"
    storage.create_run(run_id=run_id, source="https://test.api", scraped_at="2026-10-01T10:00:00+00:00")
    p1 = FPLPlayer(
        id=1, first_name="Bukayo", second_name="Saka", web_name="Saka", team="ARS", position="MID",
        price=10.0, total_points=50, event_points=5, selected_by_percent=25.0, form=6.0, goals=3, assists=4,
    )
    storage.save_current_and_snapshots(run_id=run_id, players=[p1])
    storage.complete_run(run_id=run_id, records_extracted=1, records_valid=1, records_invalid=0, records_persisted=1)
    return storage


@pytest.fixture
def two_run_storage(tmp_path: Path) -> FPLStorage:
    """Fixture providing storage with two completed runs with known deltas."""
    storage = FPLStorage(db_path=tmp_path / "fpl_hist_dual.db")

    # Run 1: Earlier snapshot
    run1_id = "fpl_20261001_100000"
    storage.create_run(run_id=run1_id, source="https://test.api", scraped_at="2026-10-01T10:00:00+00:00")
    p1_r1 = FPLPlayer(
        id=1, first_name="Bukayo", second_name="Saka", web_name="Saka", team="ARS", position="MID",
        price=10.0, total_points=50, event_points=5, selected_by_percent=25.0, form=6.0, goals=3, assists=4,
    )
    p2_r1 = FPLPlayer(
        id=2, first_name="Erling", second_name="Haaland", web_name="Haaland", team="MCI", position="FWD",
        price=15.0, total_points=80, event_points=10, selected_by_percent=60.0, form=9.0, goals=10, assists=2,
    )
    p3_r1 = FPLPlayer(
        id=3, first_name="Reece", second_name="James", web_name="James", team="CHE", position="DEF",
        price=5.5, total_points=20, event_points=2, selected_by_percent=8.0, form=3.0, goals=0, assists=1,
    )
    storage.save_current_and_snapshots(run_id=run1_id, players=[p1_r1, p2_r1, p3_r1])
    storage.complete_run(run_id=run1_id, records_extracted=3, records_valid=3, records_invalid=0, records_persisted=3)

    # Run 2: Later snapshot
    # Changes:
    # Saka: price 10.0 -> 10.2 (+0.2), points 50 -> 60 (+10), ownership 25.0 -> 28.0 (+3.0 pp), form 6.0 -> 8.0 (+2.0)
    # Haaland: price 15.0 -> 14.8 (-0.2), points 80 -> 82 (+2), ownership 60.0 -> 57.0 (-3.0 pp), form 9.0 -> 7.0 (-2.0)
    # James: price 5.5 -> 5.5 (0.0), points 20 -> 20 (0), ownership 8.0 -> 7.5 (-0.5 pp), form 3.0 -> 2.5 (-0.5)
    run2_id = "fpl_20261008_100000"
    storage.create_run(run_id=run2_id, source="https://test.api", scraped_at="2026-10-08T10:00:00+00:00")
    p1_r2 = FPLPlayer(
        id=1, first_name="Bukayo", second_name="Saka", web_name="Saka", team="ARS", position="MID",
        price=10.2, total_points=60, event_points=10, selected_by_percent=28.0, form=8.0, goals=4, assists=5,
    )
    p2_r2 = FPLPlayer(
        id=2, first_name="Erling", second_name="Haaland", web_name="Haaland", team="MCI", position="FWD",
        price=14.8, total_points=82, event_points=2, selected_by_percent=57.0, form=7.0, goals=10, assists=2,
    )
    p3_r2 = FPLPlayer(
        id=3, first_name="Reece", second_name="James", web_name="James", team="CHE", position="DEF",
        price=5.5, total_points=20, event_points=0, selected_by_percent=7.5, form=2.5, goals=0, assists=1,
    )
    storage.save_current_and_snapshots(run_id=run2_id, players=[p1_r2, p2_r2, p3_r2])
    storage.complete_run(run_id=run2_id, records_extracted=3, records_valid=3, records_invalid=0, records_persisted=3)

    return storage


def test_empty_historical_database(empty_storage: FPLStorage):
    """Verify handling when database has zero runs."""
    analytics = FPLHistoricalAnalytics(storage=empty_storage)
    latest, prev = analytics.get_latest_runs()
    assert latest is None
    assert prev is None

    result = analytics.analyze()
    assert result.summary.total_players_compared == 0
    assert result.quality.status == "empty history"
    assert result.price_increases == []


def test_one_run_history_behavior(one_run_storage: FPLStorage):
    """Verify single-run scenario gracefully reports comparison unavailable."""
    analytics = FPLHistoricalAnalytics(storage=one_run_storage)
    latest, prev = analytics.get_latest_runs()
    assert latest is not None
    assert latest["run_id"] == "fpl_20261001_100000"
    assert prev is None

    result = analytics.analyze()
    assert result.summary.total_players_compared == 0
    assert result.summary.previous_run_id is None
    assert result.quality.status == "limited history"
    assert result.price_increases == []

    # But single player history must still function
    p_hist = analytics.get_player_history(player_id=1)
    assert len(p_hist) == 1
    assert p_hist.iloc[0]["web_name"] == "Saka"


def test_latest_and_previous_run_detection(two_run_storage: FPLStorage):
    """Verify automatic detection resolves latest and immediately preceding run."""
    analytics = FPLHistoricalAnalytics(storage=two_run_storage)
    latest, prev = analytics.get_latest_runs()
    assert latest is not None
    assert prev is not None
    assert latest["run_id"] == "fpl_20261008_100000"
    assert prev["run_id"] == "fpl_20261001_100000"


def test_player_level_deltas_calculation(two_run_storage: FPLStorage):
    """Verify exact numeric delta calculations: latest minus previous."""
    analytics = FPLHistoricalAnalytics(storage=two_run_storage)
    diff_df = analytics.compare_runs(latest_run_id="fpl_20261008_100000", previous_run_id="fpl_20261001_100000")

    assert len(diff_df) == 3
    saka = diff_df[diff_df["player_id"] == 1].iloc[0]
    # Price: 10.2 - 10.0 = +0.2
    assert saka["price_change"] == 0.2
    # Points: 60 - 50 = +10
    assert saka["total_points_change"] == 10
    # Ownership: 28.0 - 25.0 = +3.0 pp
    assert saka["ownership_change_pp"] == 3.0
    # Form: 8.0 - 6.0 = +2.0
    assert saka["form_change"] == 2.0
    # Goals: 4 - 3 = +1
    assert saka["goals_change"] == 1

    haaland = diff_df[diff_df["player_id"] == 2].iloc[0]
    # Price: 14.8 - 15.0 = -0.2
    assert haaland["price_change"] == -0.2
    # Ownership: 57.0 - 60.0 = -3.0 pp
    assert haaland["ownership_change_pp"] == -3.0
    # Form: 7.0 - 9.0 = -2.0
    assert haaland["form_change"] == -2.0


def test_price_movers(two_run_storage: FPLStorage):
    """Verify price increases and decreases extraction."""
    analytics = FPLHistoricalAnalytics(storage=two_run_storage)
    diff_df = analytics.compare_runs("fpl_20261008_100000", "fpl_20261001_100000")
    inc, dec = analytics.get_price_movers(diff_df, top_n=5)

    assert len(inc) == 1
    assert inc.iloc[0]["web_name"] == "Saka"
    assert inc.iloc[0]["price_change"] == 0.2

    assert len(dec) == 1
    assert dec.iloc[0]["web_name"] == "Haaland"
    assert dec.iloc[0]["price_change"] == -0.2


def test_ownership_movers_percentage_points(two_run_storage: FPLStorage):
    """Verify ownership gainers and losers in absolute percentage points."""
    analytics = FPLHistoricalAnalytics(storage=two_run_storage)
    diff_df = analytics.compare_runs("fpl_20261008_100000", "fpl_20261001_100000")
    gainers, losers = analytics.get_ownership_movers(diff_df, top_n=5)

    assert gainers.iloc[0]["web_name"] == "Saka"
    assert gainers.iloc[0]["ownership_change_pp"] == 3.0

    assert losers.iloc[0]["web_name"] == "Haaland"
    assert losers.iloc[0]["ownership_change_pp"] == -3.0


def test_performance_movers_points_and_form(two_run_storage: FPLStorage):
    """Verify performance metrics: total points gains, form risers, and form fallers."""
    analytics = FPLHistoricalAnalytics(storage=two_run_storage)
    diff_df = analytics.compare_runs("fpl_20261008_100000", "fpl_20261001_100000")
    pts, risers, fallers = analytics.get_performance_movers(diff_df, top_n=5)

    assert pts.iloc[0]["web_name"] == "Saka"
    assert pts.iloc[0]["total_points_change"] == 10

    assert risers.iloc[0]["web_name"] == "Saka"
    assert risers.iloc[0]["form_change"] == 2.0

    assert fallers.iloc[0]["web_name"] == "Haaland"
    assert fallers.iloc[0]["form_change"] == -2.0


def test_value_movers_points_per_million(two_run_storage: FPLStorage):
    """Verify value (points per million) efficiency deltas."""
    analytics = FPLHistoricalAnalytics(storage=two_run_storage)
    diff_df = analytics.compare_runs("fpl_20261008_100000", "fpl_20261001_100000")
    improvers, decliners = analytics.get_value_movers(diff_df, top_n=5)

    # Saka PPM: run 1 = 50 / 10.0 = 5.0; run 2 = 60 / 10.2 = 5.88. Value change = +0.88
    assert improvers.iloc[0]["web_name"] == "Saka"
    assert improvers.iloc[0]["value_change"] == 0.88


def test_rising_and_falling_momentum_ranking(two_run_storage: FPLStorage):
    """Verify transparent composite momentum rankings."""
    analytics = FPLHistoricalAnalytics(storage=two_run_storage)
    diff_df = analytics.compare_runs("fpl_20261008_100000", "fpl_20261001_100000")
    rising, falling = analytics.get_rising_and_falling_players(diff_df, top_n=5)

    # Saka: (3.0 * 2) + (2.0 * 1) + (0.88 * 0.5) = 6 + 2 + 0.44 = 8.44
    assert rising.iloc[0]["web_name"] == "Saka"
    assert rising.iloc[0]["momentum_score"] == 8.44

    # Haaland: (-3.0 * 2) + (-2.0 * 1) + (value_change) is negative
    assert falling.iloc[0]["web_name"] == "Haaland"
    assert falling.iloc[0]["momentum_score"] < 0


def test_player_history_chronological_order(two_run_storage: FPLStorage):
    """Verify player history is sorted chronologically with correct snapshot count."""
    analytics = FPLHistoricalAnalytics(storage=two_run_storage)
    hist = analytics.get_player_history(player_id=1)

    assert len(hist) == 2
    assert hist.iloc[0]["run_id"] == "fpl_20261001_100000"
    assert hist.iloc[0]["price"] == 10.0
    assert hist.iloc[1]["run_id"] == "fpl_20261008_100000"
    assert hist.iloc[1]["price"] == 10.2


def test_unknown_player_history(two_run_storage: FPLStorage):
    """Verify unknown player ID returns empty DataFrame without errors."""
    analytics = FPLHistoricalAnalytics(storage=two_run_storage)
    hist = analytics.get_player_history(player_id=9999)
    assert hist.empty


def test_team_and_position_trends(two_run_storage: FPLStorage):
    """Verify team and position aggregate comparisons across runs."""
    analytics = FPLHistoricalAnalytics(storage=two_run_storage)
    teams = analytics.get_team_comparison("fpl_20261008_100000", "fpl_20261001_100000")
    assert not teams.empty
    ars = teams[teams["team"] == "ARS"].iloc[0]
    assert ars["points_change"] == 10  # Saka gained 10 pts

    positions = analytics.get_position_comparison("fpl_20261008_100000", "fpl_20261001_100000")
    assert not positions.empty
    mid = positions[positions["position"] == "MID"].iloc[0]
    assert mid["points_change"] == 10


def test_historical_quality_report_healthy(two_run_storage: FPLStorage):
    """Verify healthy status reported when runs and snapshots are consistent."""
    analytics = FPLHistoricalAnalytics(storage=two_run_storage)
    rep = analytics.get_historical_quality_report()
    assert rep.status == "healthy history"
    assert rep.total_runs == 2
    assert rep.total_snapshots == 6
    assert rep.duplicate_snapshots == 0
    assert rep.orphan_snapshots == 0
