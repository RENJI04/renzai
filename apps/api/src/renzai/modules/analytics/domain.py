"""Framework-independent analytics windows and typed dashboard results."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class AnalyticsWindow(StrEnum):
    HOURS_24 = "24h"
    DAYS_7 = "7d"
    DAYS_30 = "30d"
    DAYS_90 = "90d"


class AnalyticsSource(StrEnum):
    ANALYZE = "analyze"
    PLAYGROUND = "playground"
    GATEWAY = "gateway"


@dataclass(frozen=True, slots=True)
class WindowRange:
    name: AnalyticsWindow
    start: datetime
    end: datetime
    bucket: str
    bucket_starts: tuple[datetime, ...]


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    analyses: int
    gateway_requests: int
    threats_detected: int
    blocked: int
    require_review: int
    redacted: int
    critical_analyses: int
    open_incidents: int
    threat_rate_numerator: int
    threat_rate_denominator: int
    threat_rate_percent: float

    def serialize(self) -> dict[str, int | float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ActivityBucket:
    bucket_start: datetime
    analysis_count: int
    threat_count: int
    blocked_count: int
    review_count: int

    def serialize(self) -> dict[str, str | int]:
        return {
            "bucket_start": self.bucket_start.isoformat(),
            "analysis_count": self.analysis_count,
            "threat_count": self.threat_count,
            "blocked_count": self.blocked_count,
            "review_count": self.review_count,
        }


def window_range(window: AnalyticsWindow, as_of: datetime) -> WindowRange:
    """Return inclusive UTC range boundaries and every chart bucket start."""

    end = as_of.astimezone(UTC)
    if window is AnalyticsWindow.HOURS_24:
        bucket = "hour"
        count = 24
        current = end.replace(minute=0, second=0, microsecond=0)
        step = timedelta(hours=1)
    else:
        bucket = "day"
        count = {
            AnalyticsWindow.DAYS_7: 7,
            AnalyticsWindow.DAYS_30: 30,
            AnalyticsWindow.DAYS_90: 90,
        }[window]
        current = end.replace(hour=0, minute=0, second=0, microsecond=0)
        step = timedelta(days=1)
    start = current - step * (count - 1)
    return WindowRange(
        name=window,
        start=start,
        end=end,
        bucket=bucket,
        bucket_starts=tuple(start + step * index for index in range(count)),
    )
