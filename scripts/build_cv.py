#!/usr/bin/env python3
"""Build the CV in every configured profile.

Exit codes are deliberately distinct, because different people fix them:
  0 success
  2 usage error (bad flag, unknown profile)
  3 input data is invalid          -> edit data/
  4 a converter or tool is missing -> fix the machine
  5 publish guard violation        -> a non-public artefact nearly went public
  6 --check found drift
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from lib.bib import Bibliography  # noqa: E402
from lib.model import plain  # noqa: E402
from lib.pdf import (ConverterMissing, PdfVerificationError,  # noqa: E402
                     docx_to_pdf, scrub_dates, verify_pdf)
from lib.profile import CVProfile  # noqa: E402
from lib.render_docx import render_docx  # noqa: E402
from lib.report import Report  # noqa: E402
from lib.sections import build_document, load_config  # noqa: E402

from validate_cv_data import load_everything  # noqa: E402

EXIT_OK, EXIT_USAGE, EXIT_DATA = 0, 2, 3
EXIT_TOOL, EXIT_GUARD, EXIT_DRIFT = 4, 5, 6

BUILD_DIR = REPO / "build" / "cv"
LO_PROFILE = REPO / "build" / ".lo"

#: The ONLY files that may be written into a web-published directory.
PUBLIC_NAMES = {
    "en": Path("assets/cv/Shinichi_Namba_CV_EN.pdf"),
    "ja": Path("assets/cv/Shinichi_Namba_CV_JA.pdf"),
}
#: docs/ is the GitHub Pages root, not _site/, so it counts as published.
WEB_DIRS = [REPO / "assets", REPO / "docs", REPO / "_site"]

JA_PROBES = ("職歴", "学歴", "競争的資金", "奨学助成")


class GuardViolation(RuntimeError):
    pass


def _rel(path: Path) -> str:
    """Repo-relative when possible; --out may point anywhere."""
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path.resolve())


def _is_web(path: Path) -> bool:
    p = path.resolve()
    return any(p == w or w in p.parents for w in WEB_DIRS)


def assert_publishable(path: Path, cvp: CVProfile, doc, master) -> None:
    """Three independent layers, because this failure is publicly visible."""
    if not _is_web(path):
        return
    # 1. only a profile explicitly marked publishable may target a web dir
    if not cvp.publish_to_site:
        raise GuardViolation(
            f"refusing to write profile {cvp.name!r} "
            f"(publish_to_site={cvp.publish_to_site}) "
            f"into the web directory {path}")
    # 2. the filename must be exactly the whitelisted one
    expected = PUBLIC_NAMES.get(cvp.name)
    rel = path.resolve().relative_to(REPO)
    if expected is None or rel != expected:
        raise GuardViolation(
            f"unexpected public artefact path {rel} for profile {cvp.name!r}")
    if path.suffix.lower() != ".pdf":
        raise GuardViolation(f"only PDFs may be published, not {path.suffix}")
    # 3. NOTE: there is deliberately no per-record content check any more.
    #    The document's full block prints EVERY row, so `visible_cv_short`
    #    only decides what appears twice, not what stays private. The only
    #    way to keep something off the published CV is to remove the row, or
    #    to switch its show_*_cv_full gate off. See data/README.md.


def build_profile(cvp: CVProfile, ctx, cfg, *, formats: set[str],
                  out_dir: Path, publish: bool) -> dict:
    doc = build_document(ctx.master, ctx.profile, ctx.bib, cvp, cfg)
    result = {"profile": cvp.name, "docx": None, "pdf": None,
              "published": None, "pages": None}

    docx_path = out_dir / f"{cvp.output}.docx"
    if _is_web(docx_path):
        raise GuardViolation(f"DOCX must never be written to a web directory: "
                             f"{docx_path}")
    if "docx" in formats:
        render_docx(doc, docx_path)
        result["docx"] = _rel(docx_path)

    if "pdf" in formats:
        pdf = docx_to_pdf(docx_path, out_dir, profile_dir=LO_PROFILE)
        scrub_dates(pdf)
        urls = {r.href for s in doc.sections for e in s.entries
                for r in (*e.body, *e.date) if r.href}
        info = verify_pdf(pdf, cvp.language, expect_urls=urls,
                          probes=JA_PROBES if cvp.language == "ja" else ())
        result["pdf"] = _rel(pdf)
        result["pages"] = info["pages"]
        if info["missing_links"]:
            raise PdfVerificationError(
                f"{pdf.name}: hyperlinks lost: {info['missing_links'][:3]}")

        if publish and cvp.publish_to_site:
            dest = REPO / PUBLIC_NAMES[cvp.name]
            assert_publishable(dest, cvp, doc, ctx.master)
            dest.parent.mkdir(parents=True, exist_ok=True)
            new = pdf.read_bytes()
            # write-if-changed keeps docs/ diffs empty on a no-op rebuild
            if not dest.exists() or hashlib.sha256(dest.read_bytes()).digest() \
                    != hashlib.sha256(new).digest():
                dest.write_bytes(new)
            result["published"] = _rel(dest)
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", action="append", default=None,
                    help="profile name from data/cv_profiles.yml, or 'all'")
    ap.add_argument("--formats", default="docx,pdf")
    ap.add_argument("--out", default=str(BUILD_DIR))
    ap.add_argument("--publish", action="store_true",
                    help="copy publishable short PDFs into assets/cv/")
    ap.add_argument("--no-publish", dest="publish", action="store_false")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)

    formats = {f.strip() for f in args.formats.split(",") if f.strip()}
    bad = formats - {"docx", "pdf"}
    if bad:
        print(f"unknown format(s): {', '.join(sorted(bad))}", file=sys.stderr)
        return EXIT_USAGE
    if "pdf" in formats and "docx" not in formats:
        formats.add("docx")          # the PDF is converted from the DOCX

    rep = Report()
    ctx = load_everything(rep)
    if not rep.ok:
        print(rep.render_text(), file=sys.stderr)
        print("\ninput validation failed; nothing was built", file=sys.stderr)
        return EXIT_DATA

    names = args.profile or ["all"]
    if names == ["all"] or "all" in names:
        selected = list(ctx.cv_profiles)
    else:
        selected = names
        unknown = [n for n in selected if n not in ctx.cv_profiles]
        if unknown:
            print(f"unknown profile(s): {', '.join(unknown)}\n"
                  f"available: {', '.join(ctx.cv_profiles)}", file=sys.stderr)
            return EXIT_USAGE

    cfg = load_config()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = REPO / out_dir

    rows, worst = [], EXIT_OK
    for name in selected:
        cvp = ctx.cv_profiles[name]
        try:
            rows.append(build_profile(cvp, ctx, cfg, formats=formats,
                                      out_dir=out_dir, publish=args.publish))
        except GuardViolation as e:
            print(f"PUBLISH GUARD: {e}", file=sys.stderr)
            worst = max(worst, EXIT_GUARD)
        except ConverterMissing as e:
            print(f"MISSING TOOL: {e}", file=sys.stderr)
            worst = max(worst, EXIT_TOOL)
        except PdfVerificationError as e:
            print(f"PDF VERIFICATION FAILED: {e}", file=sys.stderr)
            worst = max(worst, EXIT_TOOL)

    if not args.quiet and rows:
        print(f"{'profile':12} {'docx':44} {'pdf':43} pages  published")
        for r in rows:
            print(f"{r['profile']:12} {r['docx'] or '-':44} "
                  f"{r['pdf'] or '-':43} {str(r['pages'] or '-'):5}  "
                  f"{r['published'] or '-'}")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
