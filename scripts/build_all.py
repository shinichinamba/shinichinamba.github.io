#!/usr/bin/env python3
"""Run the whole pipeline: validate -> site data -> CVs (-> optional Jekyll).

Exit code is the worst of the stages, so one broken step cannot hide behind a
later successful one.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(label: str, args: list[str], *, env=None) -> int:
    print(f"\n=== {label} " + "=" * max(0, 60 - len(label)))
    r = subprocess.run(args, cwd=REPO, env=env)
    if r.returncode:
        print(f"--- {label} FAILED (exit {r.returncode})", file=sys.stderr)
    return r.returncode


def jekyll_command() -> list[str]:
    """Invoke Jekyll through a LOGIN shell.

    Two environment details bite otherwise:

    * Ruby is selected by chruby from the login profile, so a bare subprocess
      inherits no GEM_HOME/GEM_PATH and Bundler raises Bundler::GemNotFound
      even though `bundle` itself is on PATH.
    * With LANG unset Ruby defaults its external encoding to US-ASCII and
      bibtex-ruby dies with "invalid byte sequence in US-ASCII" on the
      accented author names in publications.bib.
    """
    return ["bash", "-lc",
            "LANG=${LANG:-en_US.UTF-8} LC_ALL=${LC_ALL:-en_US.UTF-8} "
            "bundle exec jekyll build"]


def verify_site() -> int:
    """Assert the built site actually contains what it should.

    Featured Research is the fragile one: if a bibkey fails to interpolate,
    jekyll-scholar matches nothing and the section renders silently empty --
    no error, no warning. Counting the rendered entries turns that into a
    non-zero exit.
    """
    import yaml
    site = REPO / "_site"
    page = site / "publications" / "index.html"
    problems: list[str] = []

    if (site / "data").exists():
        problems.append("_site/data exists: the master spreadsheet would be "
                        "published. Check `exclude:` in _config.yml.")

    if not page.exists():
        problems.append("_site/publications/index.html was not built")
    else:
        html = page.read_text(encoding="utf-8")
        featured = yaml.safe_load(
            (REPO / "_data" / "featured_publications.yml").read_text("utf-8")) or []
        start = html.find('class="featured-research"')
        if start < 0:
            problems.append("Featured Research section is missing")
        else:
            end = html.lower().find("preprints", start)
            block = html[start:end if end > 0 else len(html)]
            n = block.count('<ol class="bibliography">')
            if n != len(featured):
                problems.append(
                    f"Featured Research rendered {n} entries but "
                    f"featured_publications.yml lists {len(featured)}")
            for f in featured:
                if f'id="{f["bibkey"]}"' not in block:
                    problems.append(f"featured bibkey {f['bibkey']} did not "
                                    f"render (interpolation may have failed)")
        if "{{" in html or "{%" in html:
            problems.append("unrendered Liquid found in the built page")

    for name in ("Shinichi_Namba_CV_EN.pdf", "Shinichi_Namba_CV_JA.pdf"):
        if not (site / "assets" / "cv" / name).exists():
            problems.append(f"_site/assets/cv/{name} is missing")
    extra = sorted(p.name for p in (site / "assets" / "cv").glob("*")
                   if p.name not in ("Shinichi_Namba_CV_EN.pdf",
                                     "Shinichi_Namba_CV_JA.pdf")) \
        if (site / "assets" / "cv").exists() else []
    if extra:
        problems.append(f"unexpected files published under assets/cv: {extra}")

    print(f"\n=== verify " + "=" * 54)
    if problems:
        for p in problems:
            print(f"  FAIL {p}", file=sys.stderr)
        return 1
    print("  site checks passed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-cv", action="store_true")
    ap.add_argument("--jekyll", action="store_true",
                    help="also run `bundle exec jekyll build`")
    ap.add_argument("--verify", action="store_true",
                    help="run post-build assertions (implies --jekyll)")
    args = ap.parse_args(argv)

    worst = 0
    worst = max(worst, run("validate", [PY, "scripts/validate_cv_data.py"]))
    if worst:
        return worst
    worst = max(worst, run("site data", [PY, "scripts/build_site_data.py"]))
    if worst:
        return worst
    if not args.skip_cv:
        worst = max(worst, run("cv", [PY, "scripts/build_cv.py",
                                      "--profile", "all", "--publish"]))
    if args.jekyll or args.verify:
        worst = max(worst, run("jekyll", jekyll_command()))
    if args.verify and not worst:
        worst = max(worst, verify_site())
    print("\nOK" if not worst else f"\nFAILED (exit {worst})")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
