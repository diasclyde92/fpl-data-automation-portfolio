"""Domain data model for Fantasy Premier League (FPL) players."""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FPLPlayer(BaseModel):
    """Validated data model representing an FPL player record."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    id: int = Field(..., gt=0, description="Unique FPL element/player ID")
    first_name: str = Field(..., description="Player given name")
    second_name: str = Field(..., description="Player family/surname")
    web_name: str = Field(..., min_length=1, description="Display name used on FPL kit/web interface")
    team: str = Field(..., min_length=1, description="Team short name (e.g. ARS, MCI, LIV)")
    position: str = Field(..., min_length=1, description="Position short code (GKP, DEF, MID, FWD)")
    price: float = Field(..., ge=0.0, description="Current price in millions (e.g. 6.1, 14.0)")
    total_points: int = Field(..., description="Accumulated FPL total points in season")
    event_points: int = Field(0, description="Points scored in current/latest gameweek event")
    selected_by_percent: float = Field(..., ge=0.0, le=100.0, description="Ownership selection percentage")
    goals: int = Field(0, ge=0, description="Goals scored")
    assists: int = Field(0, ge=0, description="Assists provided")
    clean_sheets: int = Field(0, ge=0, description="Clean sheets earned")
    minutes: int = Field(0, ge=0, description="Total minutes played")
    bonus: int = Field(0, ge=0, description="Total bonus points accumulated")
    form: float = Field(0.0, description="Average points per match across recent matches")
    status: str = Field("a", min_length=1, description="Availability status code ('a', 'd', 'i', 's', 'u')")
    scraped_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when record was extracted/validated",
    )

    @field_validator("web_name", "team", "position")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info) -> str:
        """Validate critical string fields are not blank."""
        stripped = v.strip()
        if not stripped:
            raise ValueError(f"{info.field_name} cannot be empty")
        return stripped
