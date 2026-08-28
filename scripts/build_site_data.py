#!/usr/bin/env python3
"""Generate _data/cv/*.yml (and the bridged profile / featured files).

Design notes worth knowing before changing anything here:

* Rows that are not ``visible_web`` are dropped at build time rather than
  carrying their flags into Liquid.  Making the templates re-filter would mean
  ~12 call sites each having to remember to do it, and forgetting produces a
  silent information leak rather than a loud failure.
* Date strings are pre-rendered for both languages.  That removes month-name
  tables, zero padding, the EN/JA format difference, the trailing "ongoing"
  dash and the missing-end_date case from Liquid entirely.
* Every one of the twelve files is written even when empty.  Liquid's
  ``concat`` filter raises on a nil argument, so a skipped file would break
  the merged sections on the Japanese page.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from lib.dates import format_range  # noqa: E402
from lib.display import format_amount  # noqa: E402
from lib.emit import write_yaml  # noqa: E402
from lib.records import Dataset, Record, record_sort_seq, sort_records  # noqa: E402
from lib.report import Report  # noqa: E402
from lib.schema import SHEETS, SHEET_ORDER, gate_columns, web_columns  # noqa: E402

from validate_cv_data import load_everything  # noqa: E402

GENERATOR = "scripts/build_site_data.py"
OUT_DIR = REPO / "_data" / "cv"

#: never leave the spreadsheet
PRIVATE = {"note", "source", "verified", "sort_order",
           "visible_web", "visible_cv_short", "visible_cv_full"}


def row_for_web(ds: Dataset, r: Record) -> dict:
    sheet = ds.sheet
    gates = gate_columns(sheet)
    out: dict = {"id": r.id}

    # dates -----------------------------------------------------------------
    primary = ds.primary_date(r)
    start = r.values.get("start_date", primary)
    end = r.values.get("end_date")
    ongoing = bool(r.values.get("ongoing"))
    out["start_date"] = (start or primary).iso() if (start or primary) else None
    if "end_date" in {c.name for c in sheet.columns}:
        out["end_date"] = end.iso() if end else None
        out["ongoing"] = ongoing
    out["date"] = {
        "en": format_range(start or primary, end, ongoing, "en"),
        "ja": format_range(start or primary, end, ongoing, "ja"),
    }
    out["sort_seq"] = record_sort_seq(ds, r)

    # payload ---------------------------------------------------------------
    for col in web_columns(sheet):
        if col.name in PRIVATE or col.kind == "date":
            continue
        if col.name in gates and not r.gate(gates[col.name], "web"):
            continue                     # value withheld: omit the key entirely
        if col.name == "amount_type" and "amount" not in out:
            continue                     # no amount shown, so it labels nothing
        if col.bilingual:
            v = r.bilingual(col.name)
            if v and (v.get("en") or v.get("ja")):
                out[col.name] = v
        elif col.kind == "money":
            amount = r.values.get(col.name)
            if amount:
                out["amount"] = {
                    "en": format_amount(amount, r.values.get("amount_type"), "en"),
                    "ja": format_amount(amount, r.values.get("amount_type"), "ja"),
                }
        else:
            v = r.values.get(col.name)
            if v not in (None, ""):
                out[col.name] = v
    return out


def build(rep: Report, *, check_only: bool = False) -> tuple[int, list[str]]:
    ctx = load_everything(rep)
    if not rep.ok:
        return 1, []

    changed: list[str] = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for key in SHEET_ORDER:
        ds = ctx.master[key]
        rows = [row_for_web(ds, r) for r in sort_records(ds)
                if bool(r.values.get("visible_web"))]
        path = OUT_DIR / f"{key}.yml"
        if check_only:
            from lib.emit import dump
            new = dump(rows)
            old = path.read_text(encoding="utf-8") if path.exists() else ""
            if new not in old:
                changed.append(str(path.relative_to(REPO)))
        elif write_yaml(path, rows, generated_by=GENERATOR):
            changed.append(str(path.relative_to(REPO)))

    # profile: drop anything the site has no business rendering
    p = dict(ctx.profile.data)
    p.pop("self_bib_aliases", None)
    if not check_only and write_yaml(REPO / "_data" / "profile.yml", p,
                                     generated_by=GENERATOR):
        changed.append("_data/profile.yml")

    # featured: normalise summary_en/summary_ja to the nested shape used
    # everywhere else, and pre-sort so Liquid never has to
    featured = [{
        "bibkey": f["bibkey"],
        "order": f.get("order"),
        "summary": {"en": f.get("summary_en"), "ja": f.get("summary_ja")},
    } for f in ctx.featured]
    if not check_only and write_yaml(REPO / "_data" / "featured_publications.yml",
                                     featured, generated_by=GENERATOR):
        changed.append("_data/featured_publications.yml")

    # remove datasets that no longer exist in the schema
    for stale in sorted(OUT_DIR.glob("*.yml")):
        if stale.stem not in SHEETS:
            if not check_only:
                stale.unlink()
            changed.append(f"{stale.relative_to(REPO)} (removed)")

    return 0, changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report what would change without writing")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    rep = Report()
    code, changed = build(rep, check_only=args.check)
    if not rep.ok or not args.quiet:
        print(rep.render_text(show_warnings=not args.quiet))
    if code:
        print("\nvalidation failed; nothing was written", file=sys.stderr)
        return 1
    if args.check:
        if changed:
            print("\nwould change:")
            for c in changed:
                print(f"  {c}")
            return 6
        print("\nup to date")
        return 0
    if changed:
        print("\nwrote:")
        for c in changed:
            print(f"  {c}")
    else:
        print("\nall generated files already up to date")
    return rep.exit_code(args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
