"""Typed records loaded from cv_master.xlsx."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .coerce import coerce_cell
from .dates import PartialDate, sort_seq
from .report import Loc, Report
from .schema import (DEPRECATED_COLUMNS, SHEETS, SHEET_ORDER, Sheet,
                     column_map, gate_flags, optional_columns,
                     physical_columns)
from .xlsx import read_sheet


@dataclass
class Record:
    sheet: str
    id: str
    values: dict[str, object]
    loc: Loc
    row: int

    def get(self, name: str, default=None):
        v = self.values.get(name, default)
        return default if v is None else v

    def bilingual(self, name: str) -> dict[str, str] | None:
        ja = self.values.get(f"{name}_ja")
        en = self.values.get(f"{name}_en")
        if not ja and not en:
            return None
        return {"en": en or None, "ja": ja or None}

    def gate(self, gate_name: str, target: str) -> bool:
        return bool(self.values.get(f"show_{gate_name}_{target}", False))


@dataclass
class Dataset:
    sheet: Sheet
    records: list[Record] = field(default_factory=list)
    #: columns actually present in the workbook, so rules can tell "absent"
    #: from "present but empty"
    present_columns: set = field(default_factory=set)

    @property
    def key(self) -> str:
        return self.sheet.key

    def visible(self, target: str) -> list[Record]:
        """Rows visible for ``web`` / ``cv_short`` / ``cv_full``."""
        col = f"visible_{target}"
        return [r for r in self.records if bool(r.values.get(col))]

    def primary_date(self, r: Record) -> PartialDate | None:
        return r.values.get(self.sheet.primary_date)  # type: ignore[return-value]


def sort_key(ds: Dataset, r: Record) -> tuple:
    d = ds.primary_date(r)
    lk = d.lower_key() if d else (0, 0, 0)
    return (-lk[0], -lk[1], -lk[2], int(r.get("sort_order", 0) or 0), r.id)


def sort_records(ds: Dataset) -> list[Record]:
    """Descending by date, ties broken by sort_order then id (a total order).

    The total order matters: docs/ is committed, so an unstable sort would
    produce a phantom diff on every build.
    """
    return sorted(ds.records, key=lambda r: sort_key(ds, r))


def record_sort_seq(ds: Dataset, r: Record) -> int:
    return sort_seq(ds.primary_date(r), int(r.get("sort_order", 0) or 0))


def load_master(path: Path, rep: Report) -> dict[str, Dataset]:
    """Read and type every sheet.  Issues accumulate in ``rep``."""
    out: dict[str, Dataset] = {}
    for key in SHEET_ORDER:
        sheet = SHEETS[key]
        expected = physical_columns(sheet)
        header, rows = read_sheet(path, key, rep)
        if not header:
            out[key] = Dataset(sheet, [], set())
            continue

        optional = optional_columns(sheet)
        missing = [c for c in expected if c not in header]
        extra = [c for c in header
                 if c not in expected and c not in DEPRECATED_COLUMNS]
        for c in missing:
            if c in optional:
                rep.warn("W-MISSING-COLUMN", Loc(path.name, key),
                         f"optional column {c!r} is absent; defaults apply")
            else:
                rep.error("E-MISSING-COLUMN", Loc(path.name, key),
                          f"required column {c!r} is missing")
        for c in extra:
            rep.warn("W-EXTRA-COLUMN", Loc(path.name, key),
                     f"column {c!r} is not in the schema and will be ignored")

        cmap = column_map(sheet)
        gates: dict[str, str] = {}
        for col in sheet.columns:
            if col.gate:
                for f in gate_flags(col.gate):
                    gates[f] = col.gate

        ds = Dataset(sheet, [], set(header))
        for rownum, cells in enumerate(rows, start=2):
            values: dict[str, object] = {}
            for phys in expected:
                if phys not in cells:
                    continue
                raw = cells[phys]
                if phys in gates:
                    from .schema import Column
                    col = Column(phys, "bool", default=False)
                elif phys in cmap:
                    col = cmap[phys]
                else:                       # bilingual half
                    base = phys.rsplit("_", 1)[0]
                    col = cmap.get(base)
                    if col is None:
                        continue
                    from .schema import Column
                    col = Column(phys, col.kind, required=False,
                                 default=col.default, web=col.web)
                values[phys] = coerce_cell(raw, col, rep)

            rid = values.get("id")
            if not rid:
                rep.error("E-REQUIRED", Loc(path.name, key, rownum, "A"),
                          "id is required")
                continue
            ds.records.append(Record(key, str(rid), values,
                                     Loc(path.name, key, rownum), rownum))
        out[key] = ds
    return out
