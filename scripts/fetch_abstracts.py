#!/usr/bin/env python3
"""Fill in missing `abstract` fields in _bibliography/*.bib.

`src/get_bibtex.R` is a record of how the .bib files were originally
assembled, not a generator that can be re-run, so abstracts are written
straight into the .bib files -- which are the authoritative copy.

Sources, tried in order for each entry that has no abstract:

1. Crossref (`api.crossref.org/works/{doi}`). Fast, but many publishers --
   Springer Nature especially -- do not deposit abstracts there.
2. PubMed (NCBI E-utilities): resolve the DOI to a PMID with esearch, then
   efetch the abstract. This is where most of this corpus is found.

Existing abstracts are never overwritten. Re-running only fills gaps, so it
is safe to run again after adding papers.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from lib.bib import Bibliography, DEFAULT_BIB_FILES, raw_keys  # noqa: E402

CONTACT = "snamba@m.u-tokyo.ac.jp"
UA = {"User-Agent": f"cv-pipeline/1.0 (mailto:{CONTACT})"}
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
#: NCBI asks for <=3 requests/second without an API key.
NCBI_DELAY = 0.40


def _get(url: str, timeout: int = 30) -> bytes:
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=timeout).read()


# --------------------------------------------------------------------------
# cleaning
# --------------------------------------------------------------------------

def strip_markup(text: str) -> str:
    """Crossref returns JATS XML; PubMed returns mixed inline tags."""
    text = re.sub(r"<jats:title[^>]*>(.*?)</jats:title>", r"\1: ", text,
                  flags=re.S | re.I)
    text = re.sub(r"</jats:p>\s*<jats:p[^>]*>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def bibtex_escape(text: str) -> str:
    """Make a value safe to drop between braces in a .bib file.

    Braces must balance or the entry stops parsing, and `%` starts a comment
    in BibTeX even inside a value.
    """
    text = text.replace("\\", r"\textbackslash{}")
    text = text.replace("{", "(").replace("}", ")")
    text = text.replace("%", r"\%")
    text = text.replace("$", r"\$").replace("#", r"\#").replace("&", r"\&")
    text = text.replace("~", r"\textasciitilde{}")
    text = text.replace("_", r"\_")
    return text


# --------------------------------------------------------------------------
# sources
# --------------------------------------------------------------------------

def from_crossref(doi: str) -> str | None:
    try:
        msg = json.loads(_get(f"https://api.crossref.org/works/"
                              f"{urllib.parse.quote(doi)}"))["message"]
    except (urllib.error.HTTPError, urllib.error.URLError,
            json.JSONDecodeError, KeyError):
        return None
    abstract = msg.get("abstract")
    return strip_markup(abstract) if abstract else None


def doi_to_pmid(doi: str) -> str | None:
    term = urllib.parse.quote(f'"{doi}"[DOI]')
    try:
        res = json.loads(_get(f"{EUTILS}/esearch.fcgi?db=pubmed&retmode=json"
                              f"&term={term}"))
    except Exception:
        return None
    ids = res.get("esearchresult", {}).get("idlist") or []
    return ids[0] if ids else None


def from_pubmed(pmid: str) -> str | None:
    try:
        xml = _get(f"{EUTILS}/efetch.fcgi?db=pubmed&retmode=xml&id={pmid}")
        root = ET.fromstring(xml)
    except Exception:
        return None
    parts = []
    for ab in root.iter("AbstractText"):
        label = ab.get("Label")
        txt = "".join(ab.itertext()).strip()
        if not txt:
            continue
        parts.append(f"{label.title()}: {txt}" if label else txt)
    text = " ".join(parts).strip()
    return strip_markup(text) if text else None


def fetch(entry) -> tuple[str | None, str]:
    doi = entry.get("doi")
    if not doi:
        return None, "no doi"
    text = from_crossref(doi)
    if text and len(text) > 120:
        return text, "crossref"
    time.sleep(NCBI_DELAY)
    pmid = entry.get("eprint") if (entry.get("eprinttype") or "").lower() == "pmid" \
        else None
    pmid = pmid or doi_to_pmid(doi)
    if not pmid:
        return None, "not in pubmed"
    time.sleep(NCBI_DELAY)
    text = from_pubmed(pmid)
    return (text, f"pubmed:{pmid}") if text else (None, "no abstract anywhere")


# --------------------------------------------------------------------------
# writing
# --------------------------------------------------------------------------

ENTRY_HEAD = re.compile(r"^([ \t]*)@(\w+)\s*\{\s*([^,\s]+)\s*,", re.M)


def insert_abstract(text: str, key: str, abstract: str) -> str:
    """Insert `abstract = {...},` as the first field of the named entry."""
    for m in ENTRY_HEAD.finditer(text):
        if m.group(3) != key:
            continue
        indent = m.group(1) + "  "
        value = bibtex_escape(abstract)
        field = f"\n{indent}abstract = {{{value}}},"
        return text[:m.end()] + field + text[m.end():]
    raise KeyError(f"entry {key} not found")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", action="append", help="restrict to these bibkeys")
    args = ap.parse_args(argv)

    bib_dir = REPO / "_bibliography"
    bib = Bibliography.load(bib_dir)
    todo = [e for e in bib.all if not e.get("abstract")]
    if args.only:
        todo = [e for e in todo if e.key in set(args.only)]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(todo)} entr(ies) without an abstract\n")

    found: dict[str, list[tuple[str, str]]] = {}
    stats = {"crossref": 0, "pubmed": 0, "missing": 0}
    for i, e in enumerate(todo, 1):
        text, src = fetch(e)
        if text:
            found.setdefault(e.source, []).append((e.key, text))
            stats["crossref" if src == "crossref" else "pubmed"] += 1
        else:
            stats["missing"] += 1
        print(f"  [{i:2}/{len(todo)}] {e.key:30} {src:22} "
              f"{len(text) if text else 0:5} chars")
        time.sleep(NCBI_DELAY)

    print(f"\ncrossref={stats['crossref']} pubmed={stats['pubmed']} "
          f"missing={stats['missing']}")
    if args.dry_run:
        print("dry run: nothing written")
        return 0

    for source, items in found.items():
        path = bib_dir / DEFAULT_BIB_FILES[source]
        text = path.read_text(encoding="utf-8")
        before = len(raw_keys(text))
        for key, abstract in items:
            text = insert_abstract(text, key, abstract)
        after = len(raw_keys(text))
        if before != after:                       # pragma: no cover - guard
            raise SystemExit(f"{path.name}: entry count changed, aborting")
        path.write_text(text, encoding="utf-8")
        print(f"wrote {len(items)} abstract(s) to {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
