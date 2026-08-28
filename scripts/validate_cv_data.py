#!/usr/bin/env python3
"""Validate every authored input before anything is generated.

Exits non-zero on a real problem, and the callers refuse to write output in
that case -- a half-migrated site is worse than none.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from lib.bib import Bibliography, DuplicateKeyError  # noqa: E402
from lib.legacy import check_against_legacy  # noqa: E402
from lib.profile import (load_cv_profiles, load_featured,  # noqa: E402
                         load_profile)
from lib.records import load_master  # noqa: E402
from lib.report import Loc, Report  # noqa: E402
from lib.schema import SHEET_ORDER, SHEETS, date_columns  # noqa: E402
from lib.validate import RULES, Ctx, validate_all  # noqa: E402
from lib.xlsx import date_precision_from_format, read_sheet  # noqa: E402


def load_everything(rep: Report, *, check_legacy: bool = True):
    data = REPO / "data"
    master = load_master(data / "cv_master.xlsx", rep)
    profile = load_profile(data / "profile.yml", rep)
    cv_profiles = load_cv_profiles(data / "cv_profiles.yml", rep)
    featured = load_featured(data / "featured_publications.yml", rep)
    try:
        bib = Bibliography.load(REPO / "_bibliography")
    except DuplicateKeyError as e:
        rep.error("E-BIB-DUP-KEY", Loc("_bibliography"), str(e),
                  "rename one of them; bibtex-ruby silently renames the "
                  "second entry, which publishes a paper under a key that "
                  "does not exist")
        bib = None
    except Exception as e:                      # pragma: no cover
        rep.error("E-BIB", Loc("_bibliography"), str(e))
        bib = None

    ctx = Ctx(master, profile, cv_profiles, featured, bib)
    validate_all(ctx, rep)
    if check_legacy:
        check_against_legacy(master, data / "legacy", rep)
    return ctx


def explain_dates() -> int:
    xlsx = REPO / "data" / "cv_master.xlsx"
    rep = Report()
    print(f"{'sheet':18} {'column':12} {'cell':6} {'raw type':10} "
          f"{'number_format':16} precision")
    print("-" * 78)
    for key in SHEET_ORDER:
        sheet = SHEETS[key]
        dates = set(date_columns(sheet))
        header, rows = read_sheet(xlsx, key, rep)
        for cells in rows:
            for name in header:
                if name not in dates:
                    continue
                rc = cells[name]
                if rc.blank:
                    continue
                prec = (date_precision_from_format(rc.number_format)
                        or "(from value)")
                print(f"{key:18} {name:12} {rc.loc.col}{rc.loc.row:<5} "
                      f"{type(rc.value).__name__:10} "
                      f"{rc.number_format:16} {prec}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as errors")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress warnings in the output")
    ap.add_argument("--no-check-legacy", action="store_true",
                    help="skip the comparison with data/legacy/*.snapshot")
    ap.add_argument("--explain-dates", action="store_true",
                    help="show how every date cell was interpreted")
    ap.add_argument("--list-rules", action="store_true")
    args = ap.parse_args(argv)

    if args.list_rules:
        for code, desc, _ in RULES:
            print(f"{code:24} {desc}")
        return 0
    if args.explain_dates:
        return explain_dates()

    rep = Report()
    load_everything(rep, check_legacy=not args.no_check_legacy)
    if args.format == "json":
        print(rep.render_json())
    else:
        print(rep.render_text(show_warnings=not args.quiet))
    return rep.exit_code(args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
