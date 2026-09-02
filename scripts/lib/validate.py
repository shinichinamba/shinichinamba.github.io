"""Cross-record validation rules.

Rules are registered in a table so the set is enumerable
(``validate_cv_data.py --list-rules``) and so adding one is a local change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .records import Dataset
from .report import Loc, Report
from .schema import SHEETS, gate_columns


@dataclass
class Ctx:
    master: dict[str, Dataset]
    profile: object
    cv_profiles: dict
    featured: list[dict]
    bib: object | None


Rule = Callable[[Ctx, Report], None]
RULES: list[tuple[str, str, Rule]] = []


def rule(code: str, desc: str):
    def deco(fn: Rule) -> Rule:
        RULES.append((code, desc, fn))
        return fn
    return deco


# --------------------------------------------------------------------------


@rule("E-DUP-ID", "ids must be unique within a sheet (and ideally globally)")
def _dup_id(ctx: Ctx, rep: Report) -> None:
    seen_global: dict[str, str] = {}
    for key, ds in ctx.master.items():
        seen: dict[str, int] = {}
        for r in ds.records:
            if r.id in seen:
                rep.error("E-DUP-ID", r.loc,
                          f"duplicate id {r.id!r} (first seen at row "
                          f"{seen[r.id]})")
            else:
                seen[r.id] = r.row
            if r.id in seen_global and seen_global[r.id] != key:
                rep.warn("W-DUP-ID-GLOBAL", r.loc,
                         f"id {r.id!r} is also used in sheet "
                         f"{seen_global[r.id]!r}",
                         "ids become HTML anchors; keep them globally unique")
            seen_global.setdefault(r.id, key)


@rule("E-DATE-ORDER", "end_date must not precede start_date")
def _date_order(ctx: Ctx, rep: Report) -> None:
    for ds in ctx.master.values():
        for r in ds.records:
            s, e = r.values.get("start_date"), r.values.get("end_date")
            if s is None or e is None:
                continue
            # Compare the widest plausible spans so 2020 vs 2020-03 is not a
            # false positive.
            if e.upper_key() < s.lower_key():
                rep.error("E-DATE-ORDER", r.loc,
                          f"end_date {e.iso()} precedes start_date {s.iso()}")


@rule("E-FEATURED-KEY", "every featured bibkey must resolve")
def _featured_keys(ctx: Ctx, rep: Report) -> None:
    if ctx.bib is None:
        return
    for i, item in enumerate(ctx.featured, start=1):
        key = item.get("bibkey")
        loc = Loc("featured_publications.yml", None, i)
        entry = ctx.bib.by_key.get(key)
        if entry is None:
            rep.error("E-FEATURED-KEY", loc,
                      f"bibkey {key!r} is not in any bibliography",
                      "check _bibliography/*.bib")
            continue
        if not entry.is_selected:
            rep.warn("W-FEATURED-NOT-SELECTED", loc,
                     f"{key} is featured but has no status=selected")
        for lang in ("en", "ja"):
            if not item.get(f"summary_{lang}"):
                rep.warn("W-MISSING-LANG", loc,
                         f"{key} has no summary_{lang}")


@rule("W-MISSING-LANG", "bilingual fields should have both halves")
def _missing_lang(ctx: Ctx, rep: Report) -> None:
    for ds in ctx.master.values():
        for col in ds.sheet.columns:
            if not col.bilingual or not col.fallback:
                continue      # a blank here is intentional, not a gap
            for r in ds.records:
                ja = r.values.get(f"{col.name}_ja")
                en = r.values.get(f"{col.name}_en")
                if bool(ja) != bool(en):
                    have, lack = ("ja", "en") if ja else ("en", "ja")
                    rep.warn("W-MISSING-LANG", r.loc,
                             f"{col.name}_{lack} is empty but "
                             f"{col.name}_{have} is set",
                             "the other language will fall back to English")


@rule("E-REQUIRED", "a required bilingual field needs at least one language")
def _required_bilingual(ctx: Ctx, rep: Report) -> None:
    for ds in ctx.master.values():
        for col in ds.sheet.columns:
            if not (col.bilingual and col.required):
                continue
            for r in ds.records:
                if not (r.values.get(f"{col.name}_ja")
                        or r.values.get(f"{col.name}_en")):
                    rep.error("E-REQUIRED", r.loc,
                              f"{col.name} is required but both "
                              f"{col.name}_ja and {col.name}_en are empty")


@rule("W-ALL-HIDDEN", "a record hidden everywhere is probably a mistake")
def _all_hidden(ctx: Ctx, rep: Report) -> None:
    for ds in ctx.master.values():
        for r in ds.records:
            if not any(r.values.get(f"visible_{t}")
                       for t in ("web", "cv_short", "cv_full")):
                rep.warn("W-ALL-HIDDEN", r.loc,
                         f"{r.id} is hidden from the site and both CVs")


@rule("W-AMOUNT-TYPE-UNKNOWN", "a stated amount should say what it measures")
def _amount_type(ctx: Ctx, rep: Report) -> None:
    for ds in ctx.master.values():
        if "amount_type" not in {c.name for c in ds.sheet.columns}:
            continue
        for r in ds.records:
            if r.values.get("amount_jpy") and \
                    (r.values.get("amount_type") in (None, "unknown")):
                rep.warn("W-AMOUNT-TYPE-UNKNOWN", r.loc,
                         f"{r.id} has an amount but amount_type is unknown")


@rule("W-NO-DATE", "records should carry their primary date")
def _no_date(ctx: Ctx, rep: Report) -> None:
    for ds in ctx.master.values():
        for r in ds.records:
            if ds.primary_date(r) is None:
                rep.warn("W-NO-DATE", r.loc,
                         f"{r.id} has no {ds.sheet.primary_date}; "
                         f"it will sort last and show no date")


@rule("W-GATE-NO-VALUE", "a display flag with nothing to display")
def _gate_without_value(ctx: Ctx, rep: Report) -> None:
    for ds in ctx.master.values():
        for name, gate in gate_columns(ds.sheet).items():
            for r in ds.records:
                if r.values.get(name):
                    continue
                on = [t for t in ("web", "cv_short", "cv_full")
                      if r.gate(gate, t)]
                if on:
                    rep.warn("W-GATE-NO-VALUE", r.loc,
                             f"{r.id}: show_{gate}_* is TRUE for {on} but "
                             f"{name} is empty")


def validate_all(ctx: Ctx, rep: Report) -> None:
    for _code, _desc, fn in RULES:
        fn(ctx, rep)
