"""Analytics package exports."""

from src.analytics.book_analytics import (
    AnalyticsResult,
    BookAnalytics,
    QualityReport,
    SummaryStats,
)
from src.analytics.fpl_analytics import (
    FPLAnalytics,
    FPLAnalyticsResult,
    FPLQualityReport,
    FPLSummaryStats,
)

__all__ = [
    "BookAnalytics",
    "AnalyticsResult",
    "SummaryStats",
    "QualityReport",
    "FPLAnalytics",
    "FPLAnalyticsResult",
    "FPLSummaryStats",
    "FPLQualityReport",
]
