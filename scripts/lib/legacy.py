"""Cross-check the migrated data against the pre-migration pages.

data/legacy/*.snapshot are frozen copies of index.md and jp.md as they stood
before the migration.  Comparing against them turns the EN/JA conflicts that
prompted this project into a mechanical checklist, and keeps working after the
live pages have been converted to Liquid.
"""

from __future__ import annotations

import re
from pathlib import Path

from .dates import DateParseError, PartialDate
from .records import Dataset
from .report import Loc, Report

BULLET = re.compile(r"^\*\s+\*\*(?P<date>[^*]+)\*\*\s*(?P<text>.+?)\s*$", re.M)
#: Setext heading: a title line followed by a run of - or =
HEADING = re.compile(r"^(?P<title>\S.*?)\s*\n[-=]{2,}\s*$", re.M)
#: Sections that are prose/announcements, not structured CV records.
SKIP_SECTIONS = {"news", "更新情報"}

_EN_MONTHS = {m.lower(): i for i, m in enumerate(
    ["", "jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"]) if i}
_EN_MONTHS.update({m.lower(): i for i, m in enumerate(
    ["", "january", "february", "march", "april", "may", "june",
     "july", "august", "september", "october", "november", "december"]) if i})


def parse_loose_date(s: str) -> PartialDate | None:
    """Parse the hand-written date forms used on the old pages."""
    s = s.strip().strip("–-").strip()
    if not s:
        return None
    m = re.match(r"^(\d{4})/(\d{1,2})(?:/(\d{1,2}))?$", s)
    if m:
        return PartialDate(int(m[1]), int(m[2]),
                           int(m[3]) if m[3] else None)
    m = re.match(r"^([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})$", s)
    if m and m[1].lower() in _EN_MONTHS:
        return PartialDate(int(m[3]), _EN_MONTHS[m[1].lower()], int(m[2]))
    m = re.match(r"^([A-Za-z]+)\s+(\d{4})$", s)
    if m and m[1].lower() in _EN_MONTHS:
        return PartialDate(int(m[2]), _EN_MONTHS[m[1].lower()])
    m = re.match(r"^(\d{4})$", s)
    if m:
        try:
            return PartialDate(int(m[1]))
        except DateParseError:
            return None
    return None


def _sections(text: str) -> list[tuple[str, str]]:
    """Split a Setext-headed Markdown page into (title, body) pairs."""
    marks = [(m.start(), m.group("title")) for m in HEADING.finditer(text)]
    out = []
    for i, (pos, title) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        out.append((title, text[pos:end]))
    return out


def legacy_entries(path: Path) -> list[tuple[PartialDate | None, PartialDate | None, str]]:
    """(start, end, text) for every dated bullet in a structured section.

    News / 更新情報 bullets are announcements rather than CV records and are
    skipped, otherwise every site-update note reads as a dropped record.
    """
    out = []
    if not path.exists():
        return out
    for title, body in _sections(path.read_text(encoding="utf-8")):
        if title.strip().lower() in SKIP_SECTIONS:
            continue
        for m in BULLET.finditer(body):
            raw = m.group("date")
            parts = [p for p in re.split(r"\s*[–-]\s*", raw) if p.strip()]
            start = parse_loose_date(parts[0]) if parts else None
            end = parse_loose_date(parts[1]) if len(parts) > 1 else None
            out.append((start, end, m.group("text").strip()))
    return out


def check_against_legacy(master: dict[str, Dataset], legacy_dir: Path,
                         rep: Report) -> None:
    """Warn about legacy start dates that no record reproduces.

    This is intentionally coarse: it flags dates that disappeared, which is
    what a migration mistake looks like.  Deliberate corrections show up here
    too and are expected -- migration_report.md records why each was made.
    """
    known: set[tuple[int, int | None]] = set()
    for ds in master.values():
        for r in ds.records:
            d = ds.primary_date(r)
            if d:
                known.add((d.year, d.month))
    for name in ("index.md.snapshot", "jp.md.snapshot"):
        path = legacy_dir / name
        for start, _end, text in legacy_entries(path):
            if start is None:
                continue
            if (start.year, start.month) not in known:
                rep.warn("W-CROSS-SOURCE", Loc(f"legacy/{name}"),
                         f"{start.iso()} ({text[:56]}) has no record with that "
                         f"start date",
                         "either a deliberate correction (see "
                         "migration_report.md) or a dropped record")
