"""Partial dates that never fabricate precision.

``2024``, ``2024-10`` and ``2024-10-15`` are three different facts and must
survive a round-trip through Excel and YAML unchanged.  Excel silently turns a
General-formatted ``2024-10`` into a real ``2024-10-01`` datetime, so the
reader recovers the intended precision from the cell's number format; this
type is what carries that decision downstream.

Display strings follow the site's existing conventions: English uses
three-letter month abbreviations, Japanese keeps the ``2024/10`` slash form
already used in jp.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

Precision = Literal["year", "month", "day"]

EN_DASH = "–"
MONTH_EN = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

_TEXT = re.compile(r"^\s*(\d{4})(?:[-/](\d{1,2})(?:[-/](\d{1,2}))?)?\s*$")


class DateParseError(ValueError):
    pass


@dataclass(frozen=True, order=True)
class PartialDate:
    year: int
    month: int | None = None
    day: int | None = None

    def __post_init__(self) -> None:
        if self.day is not None and self.month is None:
            raise DateParseError("day precision requires a month")
        if not (1000 <= self.year <= 2999):
            raise DateParseError(f"implausible year {self.year}")
        if self.month is not None and not (1 <= self.month <= 12):
            raise DateParseError(f"bad month {self.month}")
        if self.day is not None and not (1 <= self.day <= 31):
            raise DateParseError(f"bad day {self.day}")

    # -- construction -----------------------------------------------------
    @classmethod
    def parse(cls, text: str) -> "PartialDate":
        m = _TEXT.match(str(text))
        if not m:
            raise DateParseError(f"cannot parse date {text!r}")
        y, mo, d = m.group(1), m.group(2), m.group(3)
        return cls(int(y),
                   int(mo) if mo else None,
                   int(d) if d else None)

    @classmethod
    def from_datetime(cls, dt: datetime | date, precision: Precision
                      ) -> "PartialDate":
        if precision == "year":
            return cls(dt.year)
        if precision == "month":
            return cls(dt.year, dt.month)
        return cls(dt.year, dt.month, dt.day)

    @classmethod
    def coerce(cls, value) -> "PartialDate":
        if isinstance(value, PartialDate):
            return value
        if isinstance(value, (datetime, date)):
            return cls.from_datetime(value, "day")
        if isinstance(value, int):
            return cls(value)
        return cls.parse(value)

    # -- introspection ----------------------------------------------------
    @property
    def precision(self) -> Precision:
        if self.day is not None:
            return "day"
        if self.month is not None:
            return "month"
        return "year"

    def iso(self) -> str:
        if self.day is not None:
            return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
        if self.month is not None:
            return f"{self.year:04d}-{self.month:02d}"
        return f"{self.year:04d}"

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.iso()

    # -- ordering ---------------------------------------------------------
    def lower_key(self) -> tuple[int, int, int]:
        """Earliest instant the value could denote (for start dates)."""
        return (self.year, self.month or 1, self.day or 1)

    def upper_key(self) -> tuple[int, int, int]:
        """Latest instant the value could denote (for end dates)."""
        return (self.year, self.month or 12, self.day or 31)

    # -- display ----------------------------------------------------------
    def format(self, lang: str) -> str:
        if lang == "ja":
            if self.day is not None:
                return f"{self.year}/{self.month}/{self.day}"
            if self.month is not None:
                return f"{self.year}/{self.month}"
            return f"{self.year}"
        if self.day is not None:
            return f"{MONTH_EN[self.month]} {self.day}, {self.year}"
        if self.month is not None:
            return f"{MONTH_EN[self.month]} {self.year}"
        return f"{self.year}"


_ORDER = {"year": 0, "month": 1, "day": 2}
_NAME = {0: "year", 1: "month", 2: "day"}


def _demote(d: PartialDate, precision: Precision) -> PartialDate:
    if _ORDER[d.precision] <= _ORDER[precision]:
        return d
    if precision == "year":
        return PartialDate(d.year)
    return PartialDate(d.year, d.month)


def format_range(start: PartialDate | None, end: PartialDate | None,
                 ongoing: bool, lang: str) -> str:
    """Render a date range the way the current site writes it.

    ``Apr 2018 - Mar 2020`` / ``Oct 2023 -`` in English,
    ``2018/4 - 2020/3`` / ``2023/10 -`` in Japanese (with en dashes).
    Both ends are shown at the coarser of the two precisions, so a
    ``2020`` end date never makes a ``2020-03`` start look day-accurate.
    """
    if start is None and end is None:
        return ""
    if start is not None and end is not None:
        p = _NAME[min(_ORDER[start.precision], _ORDER[end.precision])]
        s, e = _demote(start, p), _demote(end, p)
        if s == e:
            return s.format(lang)
        return f"{s.format(lang)} {EN_DASH} {e.format(lang)}"
    if start is not None:
        if ongoing:
            return f"{start.format(lang)} {EN_DASH}"
        return start.format(lang)
    return f"{EN_DASH} {end.format(lang)}"


def sort_seq(d: PartialDate | None, sort_order: int = 0) -> int:
    """A single ascending integer reproducing the canonical ordering.

    Liquid can ``sort`` on this to merge several datasets under one heading
    and still get exactly the order Python produced.  Sorting ascending on
    the result is equivalent to (start_date desc, sort_order asc).
    """
    if d is None:
        ymd = 0
    else:
        y, m, dd = d.lower_key()
        ymd = y * 10000 + m * 100 + dd
    so = min(max(int(sort_order or 0), 0), 999)
    return -(ymd * 1000) + so
