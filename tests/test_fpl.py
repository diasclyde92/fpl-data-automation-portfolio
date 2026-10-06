"""Deterministic unit tests for FPL domain models, scraper, storage, pipeline, and analytics."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest
from pydantic import ValidationError

from src.analytics.fpl_analytics import FPLAnalytics
from src.models.fpl_player import FPLPlayer
from src.pipeline.fpl_pipeline import FPLPipeline
from src.scraper.exceptions import ParsingError, RequestError
from src.scraper.fpl_scraper import FPLScraper
from src.scraper.http_client import HTTPClient
from src.storage.fpl_storage import FPLStorage
from src.storage.raw_storage import RawStorage

# Minimal sample payload matching official FPL bootstrap-static structure
SAMPLE_FPL_PAYLOAD = {
    "teams": [
        {"id": 1, "name": "Arsenal", "short_name": "ARS"},
        {"id": 2, "name": "Liverpool", "short_name": "LIV"},
        {"id": 3, "name": "Manchester City", "short_name": "MCI"},
    ],
    "element_types": [
        {"id": 1, "singular_name": "Goalkeeper", "singular_name_short": "GKP"},
        {"id": 2, "singular_name": "Defender", "singular_name_short": "DEF"},
        {"id": 3, "singular_name": "Midfielder", "singular_name_short": "MID"},
        {"id": 4, "singular_name": "Forward", "singular_name_short": "FWD"},
    ],
    "elements": [
        {
            "id": 101,
            "first_name": "Bukayo",
            "second_name": "Saka",
            "web_name": "Saka",
            "team": 1,
            "element_type": 3,
            "now_cost": 100,  # £10.0m
            "total_points": 85,
            "event_points": 8,
            "selected_by_percent": "35.5",
            "goals_scored": 6,
            "assists": 7,
            "clean_sheets": 4,
            "minutes": 900,
            "bonus": 12,
            "form": "7.2",
            "status": "a",
        },
        {
            "id": 102,
            "first_name": "Erling",
            "second_name": "Haaland",
            "web_name": "Haaland",
            "team": 3,
            "element_type": 4,
            "now_cost": 150,  # £15.0m
            "total_points": 110,
            "event_points": 13,
            "selected_by_percent": "68.2",
            "goals_scored": 14,
            "assists": 3,
            "clean_sheets": 0,
            "minutes": 880,
            "bonus": 18,
            "form": "9.5",
            "status": "a",
        },
        {
            "id": 103,
            "first_name": "Alisson",
            "second_name": "Becker",
            "web_name": "Alisson",
            "team": 2,
            "element_type": 1,
            "now_cost": 55,  # £5.5m
            "total_points": 45,
            "event_points": 6,
            "selected_by_percent": "12.0",
            "goals_scored": 0,
            "assists": 0,
            "clean_sheets": 5,
            "minutes": 810,
            "bonus": 4,
            "form": "4.5",
            "status": "a",
        },
    ],
}


# ---------------------------------------------------------------------------
# 1. FPL Model Tests
# ---------------------------------------------------------------------------

def test_fpl_player_model_valid():
    """Verify valid FPL player instantiation and property types."""
    player = FPLPlayer(
        id=1,
        first_name="Mohamed",
        second_name="Salah",
        web_name="M.Salah",
        team="LIV",
        position="MID",
        price=12.5,
        total_points=95,
        event_points=10,
        selected_by_percent=45.2,
        goals=8,
        assists=6,
        clean_sheets=4,
        minutes=850,
        bonus=14,
        form=8.0,
        status="a",
    )
    assert player.id == 1
    assert player.web_name == "M.Salah"
    assert player.price == 12.5
    assert player.total_points == 95
    assert player.scraped_at is not None


def test_fpl_player_model_invalid_id():
    """Verify non-positive or 0 ID raises ValidationError."""
    with pytest.raises(ValidationError):
        FPLPlayer(
            id=0,
            first_name="Test",
            second_name="Player",
            web_name="Test",
            team="ARS",
            position="FWD",
            price=5.0,
            total_points=0,
            selected_by_percent=1.0,
        )


def test_fpl_player_model_negative_numeric():
    """Verify negative price or points raises ValidationError."""
    with pytest.raises(ValidationError):
        FPLPlayer(
            id=10,
            first_name="Test",
            second_name="Player",
            web_name="Test",
            team="ARS",
            position="FWD",
            price=-5.0,
            total_points=10,
            selected_by_percent=1.0,
        )


def test_fpl_player_model_empty_web_name():
    """Verify blank web_name raises ValidationError."""
    with pytest.raises(ValidationError):
        FPLPlayer(
            id=10,
            first_name="Test",
            second_name="Player",
            web_name="   ",
            team="ARS",
            position="FWD",
            price=5.0,
            total_points=10,
            selected_by_percent=1.0,
        )


# ---------------------------------------------------------------------------
# 2. FPL Scraper Tests
# ---------------------------------------------------------------------------

def test_fpl_scraper_extract_players():
    """Verify player extraction and team/position lookup resolution."""
    scraper = FPLScraper()
    players = scraper.extract_players(SAMPLE_FPL_PAYLOAD)

    assert len(players) == 3
    saka = players[0]
    assert saka["id"] == 101
    assert saka["web_name"] == "Saka"
    assert saka["team"] == "ARS"
    assert saka["position"] == "MID"
    assert saka["price"] == 10.0  # 100 / 10.0
    assert saka["total_points"] == 85
    assert saka["selected_by_percent"] == 35.5
    assert saka["form"] == 7.2

    haaland = players[1]
    assert haaland["id"] == 102
    assert haaland["team"] == "MCI"
    assert haaland["position"] == "FWD"
    assert haaland["price"] == 15.0


def test_fpl_scraper_invalid_json():
    """Verify invalid JSON raises ParsingError."""
    mock_client = MagicMock(spec=HTTPClient)
    mock_resp = MagicMock()
    mock_resp.text = "{invalid json"
    mock_client.get.return_value = mock_resp

    scraper = FPLScraper(client=mock_client)
    with pytest.raises(ParsingError):
        scraper.fetch_raw_data()


def test_fpl_scraper_with_raw_storage(tmp_path: Path):
    """Verify FPLScraper saves raw JSON payload when save_raw=True."""
    mock_client = MagicMock(spec=HTTPClient)
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(SAMPLE_FPL_PAYLOAD)
    mock_client.get.return_value = mock_resp

    storage = RawStorage(base_dir=tmp_path)
    scraper = FPLScraper(client=mock_client, save_raw=True, raw_storage=storage)

    records = scraper.scrape(run_id="run_fpl_test")
    assert len(records) == 3

    saved_json = tmp_path / "fpl" / "run_fpl_test" / "bootstrap.json"
    assert saved_json.exists()
    assert json.loads(saved_json.read_text(encoding="utf-8")) == SAMPLE_FPL_PAYLOAD


# ---------------------------------------------------------------------------
# 3. FPL Storage Tests
# ---------------------------------------------------------------------------

def test_fpl_storage_insert_and_retrieve(tmp_path: Path):
    """Verify inserting players and retrieving them ordered by points."""
    db_file = tmp_path / "fpl_test.db"
    storage = FPLStorage(db_path=db_file)
    assert storage.count_players() == 0

    p1 = FPLPlayer(
        id=1, first_name="A", second_name="B", web_name="P1", team="ARS", position="MID",
        price=7.0, total_points=50, event_points=5, selected_by_percent=10.0,
    )
    p2 = FPLPlayer(
        id=2, first_name="C", second_name="D", web_name="P2", team="MCI", position="FWD",
        price=14.0, total_points=120, event_points=10, selected_by_percent=55.0,
    )

    storage.insert_players([p1, p2])
    assert storage.count_players() == 2

    all_players = storage.get_all_players()
    # Ordered by total_points DESC
    assert all_players[0]["id"] == 2
    assert all_players[0]["web_name"] == "P2"
    assert all_players[1]["id"] == 1


def test_fpl_storage_upsert_on_conflict(tmp_path: Path):
    """Verify duplicate player ID updates fields rather than inserting duplicate rows."""
    storage = FPLStorage(db_path=tmp_path / "fpl_upsert.db")

    p_v1 = FPLPlayer(
        id=10, first_name="Init", second_name="Name", web_name="PlayerX", team="CHE", position="DEF",
        price=5.0, total_points=20, event_points=2, selected_by_percent=5.0,
    )
    storage.insert_player(p_v1)
    assert storage.count_players() == 1

    # Same ID, updated price & points
    p_v2 = FPLPlayer(
        id=10, first_name="Init", second_name="Name", web_name="PlayerX", team="CHE", position="DEF",
        price=5.3, total_points=35, event_points=15, selected_by_percent=12.0,
    )
    storage.insert_player(p_v2)
    assert storage.count_players() == 1

    record = storage.get_player_by_id(10)
    assert record is not None
    assert record["price"] == 5.3
    assert record["total_points"] == 35


# ---------------------------------------------------------------------------
# 4. FPL Pipeline Tests
# ---------------------------------------------------------------------------

def test_fpl_pipeline_validation_segregation(tmp_path: Path):
    """Verify pipeline separates valid players from invalid ones without crashing."""
    storage = FPLStorage(db_path=tmp_path / "fpl_pipe.db")
    pipeline = FPLPipeline(storage=storage)

    raw_records = [
        # Valid
        {
            "id": 1, "first_name": "Valid", "second_name": "One", "web_name": "One",
            "team": "LIV", "position": "MID", "price": 8.0, "total_points": 40, "selected_by_percent": 10.0,
        },
        # Invalid: ID <= 0
        {
            "id": -1, "first_name": "Bad", "second_name": "Two", "web_name": "Two",
            "team": "LIV", "position": "MID", "price": 8.0, "total_points": 40, "selected_by_percent": 10.0,
        },
        # Valid
        {
            "id": 2, "first_name": "Valid", "second_name": "Three", "web_name": "Three",
            "team": "MCI", "position": "FWD", "price": 11.0, "total_points": 60, "selected_by_percent": 20.0,
        },
    ]

    valid, invalid = pipeline.validate_records(raw_records)
    assert len(valid) == 2
    assert len(invalid) == 1
    assert valid[0].id == 1
    assert valid[1].id == 2


def test_fpl_pipeline_end_to_end_mocked(tmp_path: Path):
    """Verify complete pipeline execution using mocked scraper."""
    storage = FPLStorage(db_path=tmp_path / "fpl_run.db")
    mock_scraper = MagicMock(spec=FPLScraper)
    mock_scraper.save_raw = False
    mock_scraper.raw_storage = None
    mock_scraper.scrape.return_value = [
        {
            "id": 1, "first_name": "A", "second_name": "B", "web_name": "A.B",
            "team": "ARS", "position": "MID", "price": 7.5, "total_points": 50, "selected_by_percent": 15.0,
        }
    ]

    pipeline = FPLPipeline(scraper=mock_scraper, storage=storage)
    result = pipeline.run(endpoint_url="http://fake.api")

    assert result.records_extracted == 1
    assert result.valid_records == 1
    assert result.invalid_records == 0
    assert result.records_persisted == 1
    assert result.status == "completed"
    assert result.run_id.startswith("fpl_")
    assert storage.count_players() == 1
    assert storage.count_runs() == 1
    assert storage.count_snapshots() == 1
    assert storage.count_snapshots(run_id=result.run_id) == 1


# ---------------------------------------------------------------------------
# 5. FPL Analytics Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def populated_fpl_storage(tmp_path: Path) -> FPLStorage:
    """Fixture providing populated FPL storage with 3 players."""
    storage = FPLStorage(db_path=tmp_path / "fpl_analytics_sample.db")
    players = [
        FPLPlayer(
            id=1, first_name="Bukayo", second_name="Saka", web_name="Saka", team="ARS", position="MID",
            price=10.0, total_points=85, event_points=8, selected_by_percent=35.0,
            goals=6, assists=7, clean_sheets=4, minutes=900, bonus=12, form=7.0,
        ),
        FPLPlayer(
            id=2, first_name="Erling", second_name="Haaland", web_name="Haaland", team="MCI", position="FWD",
            price=15.0, total_points=120, event_points=13, selected_by_percent=70.0,
            goals=14, assists=3, clean_sheets=0, minutes=900, bonus=18, form=9.5,
        ),
        FPLPlayer(
            id=3, first_name="David", second_name="Raya", web_name="Raya", team="ARS", position="GKP",
            price=5.0, total_points=40, event_points=6, selected_by_percent=25.0,
            goals=0, assists=0, clean_sheets=5, minutes=900, bonus=5, form=4.0,
        ),
    ]
    storage.insert_players(players)
    return storage


def test_fpl_analytics_empty_database(tmp_path: Path):
    """Verify analytics on empty FPL database returns safe empty structures."""
    storage = FPLStorage(db_path=tmp_path / "fpl_empty.db")
    analytics = FPLAnalytics(storage=storage)
    df = analytics.load_data()

    assert df.empty
    result = analytics.analyze()
    assert result.summary.total_players == 0
    assert result.summary.average_price is None
    assert result.quality.is_empty is True
    assert result.top_points == []


def test_fpl_analytics_summary_and_metrics(populated_fpl_storage: FPLStorage):
    """Verify calculated metrics: PPM, PP90, averages, and rankings."""
    analytics = FPLAnalytics(storage=populated_fpl_storage)
    df = analytics.load_data()
    assert len(df) == 3

    # Points per million check:
    # Saka: 85 / 10.0 = 8.5
    # Haaland: 120 / 15.0 = 8.0
    # Raya: 40 / 5.0 = 8.0
    saka_row = df[df["id"] == 1].iloc[0]
    assert saka_row["points_per_million"] == 8.5

    result = analytics.analyze()
    summary = result.summary
    assert summary.total_players == 3
    # Prices: 10, 15, 5 -> Mean = 10.0, Min = 5.0, Max = 15.0
    assert summary.average_price == 10.0
    assert summary.min_price == 5.0
    assert summary.max_price == 15.0
    assert summary.total_goals_scored == 20  # 6 + 14
    assert summary.total_assists_provided == 10  # 7 + 3

    # Top points: Haaland (120) should be first
    assert result.top_points[0]["web_name"] == "Haaland"
    assert result.top_points[0]["total_points"] == 120

    # Top value (PPM): Saka (8.5) should be first
    assert result.top_value[0]["web_name"] == "Saka"
    assert result.top_value[0]["points_per_million"] == 8.5

    # Position distribution
    assert result.position_distribution == {"MID": 1, "FWD": 1, "GKP": 1}

    # Points by position: FWD (120), MID (85), GKP (40)
    assert result.points_by_position["FWD"] == 120
    assert result.points_by_position["MID"] == 85
    assert result.points_by_position["GKP"] == 40


# ---------------------------------------------------------------------------
# 6. FPL Historical Runs & Snapshots Tests (Phase 11)
# ---------------------------------------------------------------------------

def test_fpl_storage_schema_creates_runs_and_snapshots(tmp_path: Path):
    """Verify schema initialization creates fpl_runs and fpl_player_snapshots."""
    storage = FPLStorage(db_path=tmp_path / "schema_test.db")
    assert storage.count_runs() == 0
    assert storage.count_snapshots() == 0
    assert storage.count_players() == 0


def test_fpl_storage_run_lifecycle_completed(tmp_path: Path):
    """Verify creating and completing a pipeline run record."""
    storage = FPLStorage(db_path=tmp_path / "run_lifecycle.db")
    run_id = "fpl_20261006_120000"

    storage.create_run(run_id=run_id, source="https://test.api")
    latest = storage.get_latest_run()
    assert latest is not None
    assert latest["run_id"] == run_id
    assert latest["status"] == "started"

    storage.complete_run(
        run_id=run_id,
        records_extracted=10,
        records_valid=9,
        records_invalid=1,
        records_persisted=9,
        duration_seconds=1.25,
        status="completed_with_errors",
    )

    history = storage.get_run_history()
    assert len(history) == 1
    completed_run = history[0]
    assert completed_run["run_id"] == run_id
    assert completed_run["status"] == "completed_with_errors"
    assert completed_run["records_extracted"] == 10
    assert completed_run["records_persisted"] == 9
    assert completed_run["duration_seconds"] == 1.25


def test_fpl_storage_run_lifecycle_failed(tmp_path: Path):
    """Verify failing a run captures error message and failed status."""
    storage = FPLStorage(db_path=tmp_path / "run_fail.db")
    run_id = "fpl_failed_01"
    storage.create_run(run_id=run_id, source="https://fail.api")

    storage.fail_run(
        run_id=run_id,
        error_message="HTTPClient: Connection timeout after 3 retries",
        records_extracted=0,
        duration_seconds=5.0,
    )

    latest = storage.get_latest_run()
    assert latest is not None
    assert latest["status"] == "failed"
    assert "timeout" in latest["error_message"]
    assert latest["records_persisted"] == 0


def test_fpl_snapshots_multiple_runs_for_same_player_immutable(tmp_path: Path):
    """Verify that multiple snapshots for the same player across runs are preserved immutably."""
    storage = FPLStorage(db_path=tmp_path / "history_immutable.db")

    p_run1 = FPLPlayer(
        id=10, first_name="Cole", second_name="Palmer", web_name="Palmer", team="CHE", position="MID",
        price=10.5, total_points=80, event_points=8, selected_by_percent=45.0,
    )
    p_run2 = FPLPlayer(
        id=10, first_name="Cole", second_name="Palmer", web_name="Palmer", team="CHE", position="MID",
        price=10.8, total_points=95, event_points=15, selected_by_percent=52.0,
    )

    # Run 1
    storage.save_current_and_snapshots(run_id="run_1", players=[p_run1])
    assert storage.count_players() == 1
    assert storage.count_snapshots() == 1

    # Run 2
    storage.save_current_and_snapshots(run_id="run_2", players=[p_run2])
    # Current table is updated to latest (price 10.8, points 95)
    assert storage.count_players() == 1
    current = storage.get_player_by_id(10)
    assert current["price"] == 10.8
    assert current["total_points"] == 95

    # Historical snapshots table has BOTH snapshots intact
    assert storage.count_snapshots() == 2
    history = storage.get_player_history(player_id=10)
    assert len(history) == 2
    assert history[0]["run_id"] == "run_1"
    assert history[0]["price"] == 10.5
    assert history[0]["total_points"] == 80

    assert history[1]["run_id"] == "run_2"
    assert history[1]["price"] == 10.8
    assert history[1]["total_points"] == 95


def test_fpl_snapshots_uniqueness_and_idempotency(tmp_path: Path):
    """Verify that re-saving the exact same (run_id, player_id) does not duplicate rows."""
    storage = FPLStorage(db_path=tmp_path / "idempotent.db")
    player = FPLPlayer(
        id=7, first_name="Bukayo", second_name="Saka", web_name="Saka", team="ARS", position="MID",
        price=10.0, total_points=60, event_points=5, selected_by_percent=30.0,
    )

    # First save
    storage.save_snapshots(run_id="run_same", players=[player])
    assert storage.count_snapshots(run_id="run_same") == 1

    # Duplicate save with same run_id and player_id
    storage.save_snapshots(run_id="run_same", players=[player])
    assert storage.count_snapshots(run_id="run_same") == 1


def test_fpl_pipeline_creates_run_and_snapshots_end_to_end(tmp_path: Path):
    """Verify pipeline execution populates run metadata and snapshots alongside current state."""
    storage = FPLStorage(db_path=tmp_path / "pipeline_hist.db")
    mock_scraper = MagicMock(spec=FPLScraper)
    mock_scraper.save_raw = False
    mock_scraper.raw_storage = None
    mock_scraper.scrape.return_value = [
        {
            "id": 100, "first_name": "Erling", "second_name": "Haaland", "web_name": "Haaland",
            "team": "MCI", "position": "FWD", "price": 15.0, "total_points": 110,
            "selected_by_percent": 65.0,
        },
        {
            # Invalid record (missing required web_name)
            "id": 101, "first_name": "Bad", "second_name": "Player", "web_name": "   ",
            "team": "ARS", "position": "DEF", "price": 5.0, "total_points": 10,
            "selected_by_percent": 1.0,
        },
    ]

    pipeline = FPLPipeline(scraper=mock_scraper, storage=storage)
    result = pipeline.run(endpoint_url="http://mock.endpoint")

    assert result.status == "completed_with_errors"
    assert result.records_extracted == 2
    assert result.valid_records == 1
    assert result.invalid_records == 1
    assert result.records_persisted == 1

    # Verify run table
    run_record = storage.get_latest_run()
    assert run_record is not None
    assert run_record["run_id"] == result.run_id
    assert run_record["status"] == "completed_with_errors"
    assert run_record["records_valid"] == 1
    assert run_record["records_invalid"] == 1

    # Verify snapshot table
    snapshots = storage.get_snapshot(run_id=result.run_id)
    assert len(snapshots) == 1
    assert snapshots[0]["player_id"] == 100
    assert snapshots[0]["web_name"] == "Haaland"

