"""Common row schema shared by all exchange adapters."""
from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Literal
from zoneinfo import ZoneInfo

COLUMNS = [
    "exchange", "date", "holiday_name", "status", "close_time_local", "timezone",
    "close_time_utc", "session_or_product_scope", "source_url", "scraped_at_utc", "source_year",
]

Status = Literal["closed", "early_close"]


@dataclasses.dataclass
class HolidayRow:
    exchange: str
    date: dt.date
    holiday_name: str
    status: Status
    timezone: str                       # IANA, e.g. America/New_York
    source_url: str
    scraped_at_utc: dt.datetime
    source_year: int
    session_or_product_scope: str = ""
    close_time_local: dt.time | None = None   # only for early_close
    close_time_utc: dt.datetime | None = None  # derived in normalize()

    def compute_close_utc(self) -> None:
        """Convert the local early-close time to UTC using the IANA zone of the row.

        DST is handled by zoneinfo, never by a hard-coded offset: 13:00
        America/New_York is 17:00Z on 3 July (EDT, UTC-4) but 18:00Z on
        24 December (EST, UTC-5).
        """
        if self.status == "early_close" and self.close_time_local is not None:
            local = dt.datetime.combine(self.date, self.close_time_local, tzinfo=ZoneInfo(self.timezone))
            self.close_time_utc = local.astimezone(dt.timezone.utc)
        else:
            self.close_time_utc = None

    def to_record(self) -> dict:
        return {
            "exchange": self.exchange,
            "date": self.date.isoformat(),
            "holiday_name": self.holiday_name,
            "status": self.status,
            "close_time_local": self.close_time_local.strftime("%H:%M") if self.close_time_local else "",
            "timezone": self.timezone,
            "close_time_utc": self.close_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ") if self.close_time_utc else "",
            "session_or_product_scope": self.session_or_product_scope,
            "source_url": self.source_url,
            "scraped_at_utc": self.scraped_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_year": self.source_year,
        }
