"""FPL extraction component using HTTPClient to fetch and parse official bootstrap data."""

import json
import logging
from typing import Any

from src.scraper.exceptions import ParsingError, RequestError
from src.scraper.http_client import HTTPClient
from src.storage.raw_storage import RawStorage

logger = logging.getLogger(__name__)


class FPLScraper:
    """Scrapes structured FPL player records from the official Premier League API endpoint."""

    DEFAULT_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

    def __init__(
        self,
        endpoint_url: str = DEFAULT_BOOTSTRAP_URL,
        client: HTTPClient | None = None,
        save_raw: bool = False,
        raw_storage: RawStorage | None = None,
    ) -> None:
        """Initialize the FPLScraper.

        Args:
            endpoint_url: Source API endpoint URL.
            client: Optional HTTPClient instance (reuses standard retry/timeout logic).
            save_raw: Whether to save raw JSON payload to disk.
            raw_storage: Optional RawStorage instance.
        """
        self.endpoint_url = endpoint_url
        self.client = client or HTTPClient()
        self.save_raw = save_raw
        self.raw_storage = raw_storage or (RawStorage() if save_raw else None)

    def fetch_raw_data(self, url: str | None = None) -> tuple[dict[str, Any], str]:
        """Fetch payload from FPL endpoint.

        Args:
            url: Endpoint URL override.

        Returns:
            Tuple of (parsed_json_dict, raw_json_string).

        Raises:
            RequestError: If network request fails.
            ParsingError: If response is not valid JSON.
        """
        target_url = url or self.endpoint_url
        logger.info("Fetching FPL bootstrap static data from %s", target_url)

        response = self.client.get(target_url)
        raw_text = response.text

        try:
            payload = json.loads(raw_text)
            if not isinstance(payload, dict):
                raise ParsingError("FPL response root must be a JSON object")
            return payload, raw_text
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse FPL JSON response: %s", exc)
            raise ParsingError(f"Invalid JSON received from FPL endpoint: {exc}") from exc

    def extract_players(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract and normalize player records using teams and element_types lookups.

        Args:
            payload: Root dictionary from FPL bootstrap-static.

        Returns:
            List of normalized player dictionaries ready for model validation.
        """
        elements = payload.get("elements", [])
        teams_data = payload.get("teams", [])
        element_types_data = payload.get("element_types", [])

        if not isinstance(elements, list):
            raise ParsingError("Malformed FPL payload: 'elements' key is missing or not a list")

        # Build lookup tables
        team_lookup: dict[int, str] = {}
        for t in teams_data:
            if isinstance(t, dict) and "id" in t and "short_name" in t:
                team_lookup[t["id"]] = t["short_name"]

        pos_lookup: dict[int, str] = {}
        for et in element_types_data:
            if isinstance(et, dict) and "id" in et and "singular_name_short" in et:
                pos_lookup[et["id"]] = et["singular_name_short"]

        records: list[dict[str, Any]] = []

        for item in elements:
            if not isinstance(item, dict):
                continue

            try:
                player_id = int(item["id"])
                web_name = str(item.get("web_name", "")).strip()
                first_name = str(item.get("first_name", "")).strip()
                second_name = str(item.get("second_name", "")).strip()

                team_id = item.get("team")
                team_code = team_lookup.get(team_id, f"TEAM_{team_id}")

                element_type_id = item.get("element_type")
                pos_code = pos_lookup.get(element_type_id, f"POS_{element_type_id}")

                # FPL prices are integers scaled by 10 (e.g. 61 -> 6.1m)
                now_cost = float(item.get("now_cost", 0)) / 10.0
                total_points = int(item.get("total_points", 0))
                event_points = int(item.get("event_points", 0))

                # Selection percentage is stored as a string e.g. "42.3"
                selected_pct = float(item.get("selected_by_percent", 0.0))

                goals = int(item.get("goals_scored", 0))
                assists = int(item.get("assists", 0))
                clean_sheets = int(item.get("clean_sheets", 0))
                minutes = int(item.get("minutes", 0))
                bonus = int(item.get("bonus", 0))

                # Form is stored as a string e.g. "6.0"
                form = float(item.get("form", 0.0))
                status = str(item.get("status", "a")).strip()

                record = {
                    "id": player_id,
                    "first_name": first_name,
                    "second_name": second_name,
                    "web_name": web_name,
                    "team": team_code,
                    "position": pos_code,
                    "price": now_cost,
                    "total_points": total_points,
                    "event_points": event_points,
                    "selected_by_percent": selected_pct,
                    "goals": goals,
                    "assists": assists,
                    "clean_sheets": clean_sheets,
                    "minutes": minutes,
                    "bonus": bonus,
                    "form": form,
                    "status": status,
                }
                records.append(record)
            except (KeyError, ValueError, TypeError) as exc:
                logger.warning("Skipping malformed player element %s: %s", item.get("id"), exc)
                continue

        logger.info("Extracted %d normalized player records from FPL payload", len(records))
        return records

    def scrape(self, url: str | None = None, run_id: str | None = None) -> list[dict[str, Any]]:
        """Execute extraction lifecycle and optionally save raw JSON payload.

        Args:
            url: Endpoint URL override.
            run_id: Optional run ID for raw JSON preservation.

        Returns:
            List of normalized player dictionary records.
        """
        payload, raw_text = self.fetch_raw_data(url)

        if self.save_raw and self.raw_storage:
            actual_run_id = run_id or self.raw_storage.generate_run_id(prefix="fpl")
            self.raw_storage.save_json(
                dataset="fpl",
                run_id=actual_run_id,
                filename="bootstrap.json",
                json_content=raw_text,
            )

        return self.extract_players(payload)
