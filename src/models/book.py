"""Domain data models for books."""

from datetime import datetime, timezone
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Book(BaseModel):
    """Validated data model representing a scraped book record."""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    title: str = Field(..., min_length=1, description="Book title, non-empty")
    price: float = Field(..., ge=0.0, description="Price in GBP, non-negative")
    rating: int | None = Field(None, ge=1, le=5, description="Star rating scale 1 to 5")
    availability: str = Field(..., min_length=1, description="Normalized stock availability text")
    detail_url: str = Field(..., min_length=1, description="Fully qualified URL to book details")
    scraped_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when record was modeled/scraped",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is non-empty after whitespace stripping."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("title cannot be empty or purely whitespace")
        return stripped

    @field_validator("availability")
    @classmethod
    def normalize_availability(cls, v: str) -> str:
        """Normalize availability whitespace."""
        normalized = " ".join(v.split())
        if not normalized:
            raise ValueError("availability cannot be empty")
        return normalized

    @field_validator("detail_url")
    @classmethod
    def validate_detail_url(cls, v: str) -> str:
        """Validate detail_url is a well-formed HTTP/HTTPS URL."""
        parsed = urlparse(v)
        if not (parsed.scheme in {"http", "https"} and parsed.netloc):
            raise ValueError(f"detail_url must be a valid absolute HTTP/HTTPS URL: '{v}'")
        return v
