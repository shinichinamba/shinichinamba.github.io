"""The single source of truth for the cv_master.xlsx layout.

Every consumer -- the migration script, the xlsx reader, the validator, the
site-data generator and the CV builder -- derives its column list from here.
Nothing else may hard-code a column name.

Bilingual columns are declared once and expand to ``<name>_ja`` / ``<name>_en``.
Gated columns (``gate=...``) automatically grow their three ``show_*`` boolean
flags, so the six grant display flags in the spec are never written by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["str", "bool", "int", "date", "enum", "money"]
TARGETS = ("web", "cv_short", "cv_full")


@dataclass(frozen=True)
class Column:
    name: str
    kind: Kind = "str"
    bilingual: bool = False
    required: bool = False
    enum: tuple[str, ...] | None = None
    default: object = None
    web: bool = False          # emitted into _data/cv/*.yml
    gate: str | None = None    # -> show_<gate>_web / _cv_short / _cv_full
    optional: bool = False     # the column may be absent from the sheet
    #: When False, a blank in one language stays blank rather than borrowing
    #: the other language's value. Use it where an empty cell is a deliberate
    #: editorial choice rather than a missing translation.
    fallback: bool = True
    aliases: tuple[tuple[str, str], ...] = ()   # (written, canonical)

    def physical(self) -> list[str]:
        if self.bilingual:
            return [f"{self.name}_ja", f"{self.name}_en"]
        return [self.name]


@dataclass(frozen=True)
class Sheet:
    key: str
    columns: tuple[Column, ...]
    primary_date: str = "start_date"
    heading: dict[str, str] = field(default_factory=dict)
    #: field order used by the generic renderers, per language
    display_en: tuple[str, ...] = ()
    display_ja: tuple[str, ...] = ()


# --------------------------------------------------------------------------
# building blocks
# --------------------------------------------------------------------------

IDENT = (
    Column("id", "str", required=True, web=True),
)

DATE_RANGE = (
    Column("start_date", "date", web=True),
    Column("end_date", "date", web=True),
    # No `ongoing` column: it is derived from end_date (lib.dates.is_ongoing),
    # so the two can never contradict each other.
)

ADMIN = (
    Column("sort_order", "int", default=0, optional=True),
    Column("visible_web", "bool", required=True),
    #: Gates the abridged CV block only. The full block shows every row, so
    #: there is deliberately no visible_cv_full column.
    Column("visible_cv_short", "bool", required=True),
)

APPOINTMENT_TYPES = ("primary", "invited", "adjunct", "visiting", "other")
GRANT_ROLES = ("PI", "Co-I", "Collaborator", "Other")
AMOUNT_TYPES = ("total_project", "direct_cost", "personal_allocation", "unknown")
ACTIVITY_TYPES = ("lecture", "laboratory", "seminar", "teaching_assistant",
                  "supervision", "other")
TALK_TYPES = ("invited", "keynote", "seminar", "symposium", "other")
REVIEW_TYPES = ("journal", "grant", "conference", "other")
COMMITTEE_TYPES = ("society", "conference", "institutional",
                   "research_consortium", "other")
PATENT_STATUS = ("filed", "published", "granted", "abandoned", "other")


def _sheet(key, body, *, dates=DATE_RANGE, primary_date="start_date",
           heading=None, display_en=(), display_ja=()) -> Sheet:
    return Sheet(
        key=key,
        columns=IDENT + dates + tuple(body) + ADMIN,
        primary_date=primary_date,
        heading=heading or {},
        display_en=display_en,
        display_ja=display_ja,
    )


SHEETS: dict[str, Sheet] = {
    "appointments": _sheet(
        "appointments",
        [Column("position", bilingual=True, required=True, web=True),
         Column("department", bilingual=True, web=True),
         Column("institution", bilingual=True, required=True, web=True),
         Column("location", bilingual=True, web=True),
         Column("appointment_type", "enum", enum=APPOINTMENT_TYPES,
                required=True, web=True)],
        heading={"en": "Academic Appointments", "ja": "職歴"},
        display_en=("position", "department", "institution", "location"),
        display_ja=("institution", "department", "position"),
    ),
    "clinical_training": _sheet(
        "clinical_training",
        [Column("position", bilingual=True, required=True, web=True),
         Column("institution", bilingual=True, required=True, web=True),
         Column("department", bilingual=True, web=True),
         Column("location", bilingual=True, web=True)],
        heading={"en": "Clinical Training", "ja": "臨床研修"},
        display_en=("position", "department", "institution", "location"),
        display_ja=("institution", "department", "position"),
    ),
    "education": _sheet(
        "education",
        # Japanese CVs name the school rather than a bachelor's degree, so a
        # blank degree_ja is intentional and must not fall back to "M.D.".
        [Column("degree", bilingual=True, web=True, fallback=False),
         Column("field", bilingual=True, web=True),
         Column("department", bilingual=True, web=True),
         Column("institution", bilingual=True, required=True, web=True),
         Column("advisor", bilingual=True),
         Column("location", bilingual=True, web=True)],
        heading={"en": "Education", "ja": "学歴"},
        display_en=("degree", "field", "department", "institution", "location"),
        display_ja=("institution", "department", "field", "degree"),
    ),
    "awards": _sheet(
        "awards",
        [Column("award", bilingual=True, required=True, web=True),
         Column("organization", bilingual=True, web=True),
         Column("description", bilingual=True)],
        dates=(Column("award_date", "date", required=True, web=True),),
        primary_date="award_date",
        heading={"en": "Honors and Awards", "ja": "受賞歴"},
        display_en=("award", "organization"),
        display_ja=("organization", "award"),
    ),
    "fellowships": _sheet(
        "fellowships",
        [Column("fellowship", bilingual=True, required=True, web=True),
         Column("organization", bilingual=True, web=True),
         Column("amount_jpy", "money", gate="amount", web=True),
         Column("description", bilingual=True)],
        heading={"en": "Fellowships", "ja": "奨学金・フェローシップ"},
        display_en=("fellowship", "organization"),
        display_ja=("organization", "fellowship"),
    ),
    "grants": _sheet(
        "grants",
        [Column("agency", bilingual=True, required=True, web=True),
         Column("program", bilingual=True, web=True),
         Column("title", bilingual=True, web=True),
         Column("role", "enum", enum=GRANT_ROLES, required=True, web=True,
                aliases=(("co-investigator", "Co-I"), ("coinvestigator", "Co-I"),
                         ("co-i", "Co-I"), ("coi", "Co-I"),
                         ("principal investigator", "PI"),
                         ("principal-investigator", "PI"),
                         ("研究代表者", "PI"), ("研究分担者", "Co-I"),
                         ("collaborator", "Collaborator"),
                         ("連携研究者", "Collaborator"))),
         Column("grant_number", "str", gate="grant_number", web=True),
         Column("amount_jpy", "money", gate="amount", web=True),
         Column("amount_type", "enum", enum=AMOUNT_TYPES,
                default="unknown", web=True),
         Column("url", "str")],
        heading={"en": "Research Funding", "ja": "研究費"},
        display_en=("agency", "program", "title"),
        display_ja=("agency", "program", "title"),
    ),
    "teaching": _sheet(
        "teaching",
        [Column("course", bilingual=True, required=True, web=True),
         Column("activity_type", "enum", enum=ACTIVITY_TYPES,
                default="lecture", web=True,
                aliases=(("teaching assistant", "teaching_assistant"),
                         ("ta", "teaching_assistant"),
                         ("ティーチングアシスタント", "teaching_assistant"),
                         ("演習", "seminar"), ("講義", "lecture"),
                         ("実習", "laboratory"), ("指導", "supervision"))),
         Column("institution", bilingual=True, required=True, web=True),
         Column("school", bilingual=True, web=True),
         Column("role", bilingual=True, web=True)],
        heading={"en": "Teaching Experience", "ja": "教育歴"},
        display_en=("course", "school", "institution"),
        display_ja=("course", "institution", "school"),
    ),
    "invited_talks": _sheet(
        "invited_talks",
        [Column("title", bilingual=True, required=True, web=True),
         Column("event", bilingual=True, web=True),
         Column("host", bilingual=True, web=True),
         Column("location", bilingual=True, web=True),
         Column("talk_type", "enum", enum=TALK_TYPES,
                default="invited", web=True),
         Column("url", "str", web=True)],
        dates=(Column("date", "date", required=True, web=True),),
        primary_date="date",
        heading={"en": "Invited Talks", "ja": "招待講演"},
        display_en=("title", "event", "location"),
        display_ja=("event", "location", "title"),
    ),
    "reviewing": _sheet(
        "reviewing",
        [Column("review_type", "enum", enum=REVIEW_TYPES,
                default="journal", web=True),
         Column("organization", bilingual=True, web=True),
         Column("journal_or_program", bilingual=True, required=True, web=True),
         Column("count", "int")],
        dates=(Column("year", "date", web=True),),
        primary_date="year",
        heading={"en": "Peer Review Service", "ja": "査読活動"},
        display_en=("journal_or_program", "organization"),
        display_ja=("journal_or_program", "organization"),
    ),
    "committees": _sheet(
        "committees",
        [Column("committee", bilingual=True, web=True),
         Column("organization", bilingual=True, required=True, web=True),
         Column("role", bilingual=True, web=True),
         Column("committee_type", "enum", enum=COMMITTEE_TYPES,
                default="society", web=True)],
        heading={"en": "Professional Service", "ja": "委員会活動"},
        display_en=("role", "committee", "organization"),
        display_ja=("organization", "committee", "role"),
    ),
    "patents": _sheet(
        "patents",
        [Column("title", bilingual=True, required=True, web=True),
         Column("inventors", "str"),
         Column("application_number", "str"),
         Column("patent_number", "str"),
         Column("jurisdiction", "str", web=True),
         Column("grant_date", "date"),
         Column("status", "enum", enum=PATENT_STATUS,
                default="filed", web=True),
         Column("url", "str", web=True)],
        dates=(Column("filing_date", "date", required=True, web=True),),
        primary_date="filing_date",
        heading={"en": "Patents", "ja": "特許"},
        display_en=("title",),
        display_ja=("title",),
    ),
    "memberships": _sheet(
        "memberships",
        [Column("organization", bilingual=True, required=True, web=True),
         Column("membership_type", bilingual=True, web=True)],
        heading={"en": "Professional Memberships", "ja": "所属学会"},
        display_en=("organization",),
        display_ja=("organization",),
    ),
}

SHEET_ORDER: tuple[str, ...] = tuple(SHEETS)

#: Columns from earlier versions of the schema. Still tolerated in the
#: workbook so an existing file keeps loading, but ignored; they can be
#: deleted whenever convenient.
DEPRECATED_COLUMNS = frozenset({"visible_cv_full"})


# --------------------------------------------------------------------------
# derived helpers -- the only sanctioned way to enumerate columns
# --------------------------------------------------------------------------

def gate_flags(gate: str) -> list[str]:
    return [f"show_{gate}_{t}" for t in TARGETS]


def no_fallback_columns(sheet: Sheet) -> set[str]:
    """Bilingual columns where a blank must stay blank."""
    return {c.name for c in sheet.columns if c.bilingual and not c.fallback}


def optional_columns(sheet: Sheet) -> set[str]:
    """Columns whose absence from the sheet is tolerated."""
    out = set()
    for c in sheet.columns:
        if c.optional:
            out.update(c.physical())
    return out


def physical_columns(sheet: Sheet) -> list[str]:
    """Header row for a sheet, in canonical order, gates expanded."""
    out: list[str] = []
    for c in sheet.columns:
        out.extend(c.physical())
        if c.gate:
            out.extend(gate_flags(c.gate))
    return out


def gate_columns(sheet: Sheet) -> dict[str, str]:
    """``{'amount_jpy': 'amount', ...}`` for the gated columns of a sheet."""
    return {c.name: c.gate for c in sheet.columns if c.gate}


def column_map(sheet: Sheet) -> dict[str, Column]:
    return {c.name: c for c in sheet.columns}


def bool_columns(sheet: Sheet) -> list[str]:
    out = [c.name for c in sheet.columns if c.kind == "bool"]
    for c in sheet.columns:
        if c.gate:
            out.extend(gate_flags(c.gate))
    return out


def web_columns(sheet: Sheet) -> list[Column]:
    return [c for c in sheet.columns if c.web]


def date_columns(sheet: Sheet) -> list[str]:
    return [c.name for c in sheet.columns if c.kind == "date"]
