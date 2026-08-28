"""Cell -> typed value, with a loud, specific complaint on every failure.

The error messages name the fix, not just the problem: the person reading them
is editing a spreadsheet, not a Python file.
"""

from __future__ import annotations

import unicodedata
from datetime import date, datetime

from .dates import DateParseError, PartialDate
from .report import Report
from .schema import Column
from .xlsx import RawCell, date_precision_from_format

_MISSING = object()


def coerce_cell(raw: RawCell, col: Column, rep: Report):
    """Return the typed value for one cell, or None."""
    if raw.blank:
        if col.required:
            rep.error("E-REQUIRED", raw.loc,
                      f"{col.name} is required but empty")
            return None
        return col.default

    v = raw.value
    kind = col.kind

    # ---- bool -----------------------------------------------------------
    if kind == "bool":
        if isinstance(v, bool):
            return v
        rep.error("E-BAD-BOOL", raw.loc,
                  f"{col.name} must be a real TRUE/FALSE boolean, got "
                  f"{type(v).__name__} {v!r}",
                  "type TRUE or FALSE unquoted into a General-formatted cell; "
                  "text \"TRUE\", 1/0 and yes/no are all rejected so that a "
                  "mistyped flag can never be read as switched on")
        return None

    # ---- int ------------------------------------------------------------
    if kind == "int":
        if isinstance(v, bool):
            rep.error("E-BAD-INT", raw.loc, f"{col.name} is a boolean")
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float) and v.is_integer():
            return int(v)
        if isinstance(v, str) and v.strip().lstrip("-").isdigit():
            return int(v.strip())
        rep.error("E-BAD-INT", raw.loc,
                  f"{col.name} must be a whole number, got {v!r}")
        return None

    # ---- money ----------------------------------------------------------
    if kind == "money":
        if isinstance(v, bool):
            rep.error("E-BAD-MONEY", raw.loc, f"{col.name} is a boolean")
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float) and v.is_integer():
            return int(v)
        rep.error("E-BAD-MONEY", raw.loc,
                  f"{col.name} must be a bare number, got {v!r}",
                  "use the cell's number format for the currency symbol and "
                  "thousands separators, not literal text")
        return None

    # ---- date -----------------------------------------------------------
    if kind == "date":
        if isinstance(v, (datetime, date)):
            precision = date_precision_from_format(raw.number_format)
            if precision is None:
                precision = "day" if v.day != 1 else "month"
                rep.warn("W-DATE-PRECISION-GUESS", raw.loc,
                         f"{col.name} is a real date in a "
                         f"{raw.number_format!r}-formatted cell; assuming "
                         f"{precision} precision",
                         "format the column as Text and retype the value "
                         "exactly as it should be published")
            return PartialDate.from_datetime(v, precision)
        if isinstance(v, int):
            try:
                return PartialDate(v)
            except DateParseError as e:
                rep.error("E-BAD-DATE", raw.loc, f"{col.name}: {e}")
                return None
        if isinstance(v, str):
            s = v.strip()
            try:
                pd = PartialDate.parse(s)
            except DateParseError as e:
                rep.error("E-BAD-DATE", raw.loc, f"{col.name}: {e}",
                          "use YYYY, YYYY-MM or YYYY-MM-DD")
                return None
            if "/" in s:
                rep.warn("W-DATE-SEPARATOR", raw.loc,
                         f"{col.name} uses '/'; normalised to {pd.iso()}")
            return pd
        rep.error("E-BAD-DATE", raw.loc,
                  f"{col.name} has unexpected type {type(v).__name__}")
        return None

    # ---- enum -----------------------------------------------------------
    if kind == "enum":
        s = str(v).strip()
        allowed = col.enum or ()
        for a in allowed:
            if s.lower() == a.lower():
                return a
        for written, canonical in col.aliases:
            if s.lower() == written.lower():
                return canonical
        rep.error("E-BAD-ENUM", raw.loc,
                  f"{col.name} must be one of {', '.join(allowed)}, got {s!r}",
                  f"accepted spellings also include: "
                  f"{', '.join(w for w, _ in col.aliases)}"
                  if col.aliases else None)
        return None

    # ---- str ------------------------------------------------------------
    if isinstance(v, (datetime, date)):
        rep.error("E-STR-DATE", raw.loc,
                  f"{col.name} was converted to a date by Excel ({v})",
                  "format the column as Text and retype, or prefix the value "
                  "with an apostrophe")
        return None
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))          # 12345678.0 -> "12345678"
    s = str(v).strip()
    return unicodedata.normalize("NFC", s) or None
