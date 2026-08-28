"""BibTeX loading, author normalization and Nature-style citation rendering.

Tokenizing is delegated to ``bibtexparser`` (pinned to 1.4.4, the stable
release; the 2.x line has only ever shipped betas).  Everything the library
does not solve is implemented here:

* repair of the malformed ``\a'`` accent form and general de-LaTeX,
* extraction of the ``*`` / ``**`` contribution markers that are embedded
  inside the author strings,
* normalization of the two coexisting name orders (``Family, Given`` and
  ``Given Family``),
* the Nature-style citation string and the ``et al.`` collapse, both of which
  must match what ``_plugins/jekyll_scholar.rb`` renders on the website.

IMPORTANT -- duplicate keys.  bibtexparser 1.x exposes entries through a dict
keyed by ID, so a duplicate key would silently collapse two papers into one.
We therefore scan the *raw text* for keys before handing anything to the
parser, and assert that the parsed entry count matches.  The check must never
depend on parser output, because by then the collapse has already happened.
"""

from __future__ import annotations

import html as _html
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser

from .model import Run

# --------------------------------------------------------------------------
# raw scanning (must run before the parser -- see module docstring)
# --------------------------------------------------------------------------

RAW_ENTRY = re.compile(r"^[ \t]*@(\w+)\s*\{\s*([^,\s]+)\s*,", re.M)


def raw_keys(text: str) -> list[str]:
    """Every entry key in file order, straight from the source text."""
    return [m.group(2) for m in RAW_ENTRY.finditer(text)]


# --------------------------------------------------------------------------
# de-LaTeX
# --------------------------------------------------------------------------

_ACCENTS = {
    "'": "\u0301", "`": "\u0300", '"': "\u0308", "^": "\u0302", "~": "\u0303",
    "=": "\u0304", ".": "\u0307", "c": "\u0327", "u": "\u0306", "v": "\u030C",
    "H": "\u030B", "k": "\u0328", "r": "\u030A",
}

_LIGATURES = {
    r"\o": "ø", r"\O": "Ø", r"\ae": "æ", r"\AE": "Æ", r"\aa": "å", r"\AA": "Å",
    r"\ss": "ß", r"\l": "ł", r"\L": "Ł", r"\i": "ı", r"\j": "ȷ",
    r"\&": "&", r"\%": "%", r"\_": "_", r"\$": "$", r"\#": "#",
    r"\textendash": "\u2013", r"\textemdash": "\u2014",
    r"\textquoteright": "\u2019", r"\textquoteleft": "\u2018",
}

# \'a   \'{a}   {\'a}   {\'{a}}
_ACC_RE = re.compile(r"\\([`'\"^~=.cuvHkr])\s*\{?\s*(\w)\s*\}?")


def delatex(s: str) -> str:
    """Convert LaTeX escapes to Unicode, then drop protective braces.

    Order matters: the malformed ``\a'`` alignment-tab accent form (present in
    ``C{\\a'a}rcel-M{\\a'a}rquez`` and friends) is rewritten to ``\\'`` first,
    ligatures and accents are expanded next, and braces are stripped last --
    stripping first would destroy grouping such as ``{Le Grand}``.
    """
    if not s:
        return s
    # 1. repair the tabbing-environment accent form: \a'a -> \'a
    s = re.sub(r"\\a([`'\"^~=.])", r"\\\1", s)
    # 2. ligatures / escaped punctuation (longest first so \AA beats \A)
    for src in sorted(_LIGATURES, key=len, reverse=True):
        s = s.replace(src, _LIGATURES[src])
    # 3. accents
    s = _ACC_RE.sub(lambda m: m.group(2) + _ACCENTS[m.group(1)], s)
    # 4. leftover control sequences we do not understand: keep the argument
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)
    # 5. protective braces
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    return unicodedata.normalize("NFC", s)


#: Codepoints that Times New Roman does not carry, mapped to what it does.
#: LibreOffice renders a missing glyph as a hollow box rather than failing, and
#: the text still extracts cleanly, so neither the converter's exit status nor
#: a pdftotext check would catch this -- it has to be fixed at the source.
GLYPH_SUBSTITUTIONS = {
    "\u2010": "-",   # HYPHEN            (in "first-step FIB4")
    "\u2011": "-",   # NON-BREAKING HYPHEN
    "\u2012": "\u2013",  # FIGURE DASH -> EN DASH
    "\u2043": "-",   # HYPHEN BULLET
    "\u00ad": "",    # SOFT HYPHEN
}


def normalize_glyphs(s: str) -> str:
    for src, dst in GLYPH_SUBSTITUTIONS.items():
        s = s.replace(src, dst)
    return s


def _ascii_fold(s: str) -> str:
    return (
        unicodedata.normalize("NFKD", s)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


# --------------------------------------------------------------------------
# authors
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Author:
    family: str
    given: str
    initials: str          # "S." / "Y. N." / "M.-J."
    eq: bool = False       # one  *  -> equal contribution
    corr: bool = False     # two ** -> (co-)corresponding author

    @property
    def marker(self) -> str:
        return "**" if self.corr else ("*" if self.eq else "")

    @property
    def display(self) -> str:
        """``Namba, S`` -- no trailing period; the caller adds it."""
        return f"{self.family}, {self.initials}".rstrip(".")

    @property
    def sort_key(self) -> tuple[str, str]:
        return (_ascii_fold(self.family), _ascii_fold(self.initials))


def split_authors(raw: str) -> list[str]:
    """Split a BibTeX author field on ` and ` at brace depth 0."""
    out, buf, depth, i = [], [], 0, 0
    while i < len(raw):
        ch = raw[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        if depth == 0 and raw.startswith(" and ", i):
            out.append("".join(buf))
            buf = []
            i += 5
            continue
        buf.append(ch)
        i += 1
    if buf:
        out.append("".join(buf))
    return [t.strip() for t in out if t.strip()]


def _initials(given: str) -> str:
    """``Yuriko N.`` -> ``Y. N.``; ``Marie-Julie`` -> ``M.-J.``.

    Mirrors the CSL ``initialize-with=". "`` behaviour used by custom.csl.
    """
    parts = [p for p in re.split(r"\s+", given.strip()) if p]
    chunks: list[str] = []
    for p in parts:
        subs = [s for s in p.split("-") if s]
        letters = [s[0].upper() for s in subs if s and s[0].isalpha()]
        if letters:
            chunks.append(".-".join(letters) + ".")
    return " ".join(chunks)


def _top_level_comma(s: str) -> int:
    depth = 0
    for i, ch in enumerate(s):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            return i
    return -1


def _split_given_family(token: str) -> tuple[str, str]:
    """Return ``(family, given)`` for a marker-free author token."""
    c = _top_level_comma(token)
    if c >= 0:                                   # "Family, Given"
        return token[:c].strip(), token[c + 1:].strip()
    # "Given ... Family" -- the family is the last chunk, unless that chunk is
    # a brace group ("Quentin {Le Grand}", "Marion {van Vugt}").
    m = re.search(r"\{[^{}]*\}\s*$", token)
    if m:
        return token[m.start():].strip(), token[: m.start()].strip()
    parts = token.rsplit(" ", 1)
    if len(parts) == 1:
        return token.strip(), ""
    return parts[1].strip(), parts[0].strip()


def parse_author(token: str) -> Author:
    """Parse one author token, extracting the ``*`` / ``**`` markers.

    Markers prefix the *family* name in both name orders
    (``**Namba, Shinichi`` and ``Shinichi *Namba``), so we record the widest
    run of asterisks anywhere in the token and then strip them all.
    """
    runs = re.findall(r"\*+", token)
    stars = max((len(r) for r in runs), default=0)
    token = token.replace("*", "")
    family_raw, given_raw = _split_given_family(token)
    family = delatex(family_raw)
    given = delatex(given_raw)
    return Author(
        family=family,
        given=given,
        initials=_initials(given),
        eq=(stars == 1),
        corr=(stars >= 2),
    )


def parse_authors(raw: str) -> list[Author]:
    """Parse and de-duplicate an author list.

    Consortium papers list some people twice (once individually, once in the
    consortium banner).  We keep the first occurrence and merge the markers.
    This is a deliberate divergence from the website, which does not dedupe.
    """
    seen: dict[tuple[str, str], int] = {}
    out: list[Author] = []
    for tok in split_authors(raw):
        a = parse_author(tok)
        k = a.sort_key
        if k in seen:
            prev = out[seen[k]]
            if (a.eq and not prev.eq) or (a.corr and not prev.corr):
                out[seen[k]] = Author(
                    prev.family, prev.given, prev.initials,
                    eq=prev.eq or a.eq, corr=prev.corr or a.corr,
                )
            continue
        seen[k] = len(out)
        out.append(a)
    return out


# --------------------------------------------------------------------------
# entries
# --------------------------------------------------------------------------


@dataclass
class BibEntry:
    key: str
    etype: str
    fields: dict[str, str]
    order: int
    source: str                       # "publications" / "preprints" / "reviews_ja"
    _authors: list[Author] | None = field(default=None, repr=False)

    def get(self, name: str, default: str | None = None) -> str | None:
        v = self.fields.get(name.lower())
        return v if v not in (None, "") else default

    @property
    def authors(self) -> list[Author]:
        if self._authors is None:
            self._authors = parse_authors(self.fields.get("author", ""))
        return self._authors

    @property
    def is_selected(self) -> bool:
        return (self.get("status") or "").strip().lower() == "selected"

    @property
    def year(self) -> str:
        return self.get("year") or ""

    @property
    def doi(self) -> str | None:
        return self.get("doi")

    @property
    def doi_url(self) -> str | None:
        d = self.doi
        return f"https://doi.org/{d}" if d else self.get("url")


def _scalar(v) -> str:
    """Flatten a bibtexparser value to a plain string.

    With ``interpolate_strings=False`` the bare, unbraced values in this corpus
    (``status = selected``, ``month=feb``) arrive as ``BibDataStringExpression``
    rather than ``str``.  We resolve them to their literal text instead of
    expanding them as macros, which is exactly what we want for ``status``.
    """
    if isinstance(v, str):
        return v
    expr = getattr(v, "expr", None)
    if expr is not None:
        parts = []
        for x in expr:
            if isinstance(x, str):
                parts.append(x)
            else:
                parts.append(getattr(x, "name", None) or str(x))
        return "".join(parts)
    return str(v)


#: Fields that carry human-readable prose and therefore get de-LaTeX'd on load.
#: ``author`` is deliberately excluded -- it must keep its braces until
#: :func:`split_authors` has run, or ``{Le Grand}`` grouping is destroyed.
TEXT_FIELDS = ("title", "journal", "booktitle", "publisher", "series",
               "title_ja", "note")


def _parser() -> BibTexParser:
    p = BibTexParser(common_strings=False)
    # Keep field names as written; we lower-case them ourselves so that the
    # DOI/doi and ISSN/issn mixture collapses predictably.
    p.homogenize_fields = False
    p.ignore_nonstandard_types = False
    p.interpolate_strings = False        # `status = selected` stays literal
    return p


class DuplicateKeyError(ValueError):
    pass


def load_bib(path: Path, source: str) -> list[BibEntry]:
    """Parse one .bib file, refusing to proceed if keys are not unique."""
    text = Path(path).read_text(encoding="utf-8")
    keys = raw_keys(text)
    dups = sorted(k for k, n in Counter(keys).items() if n > 1)
    if dups:
        raise DuplicateKeyError(
            f"{path}: duplicate bibkey(s) {dups}. bibtexparser keys entries by "
            f"ID, so duplicates silently drop a paper; rename them in the .bib."
        )
    db = bibtexparser.loads(text, parser=_parser())
    if len(db.entries) != len(keys):
        raise ValueError(
            f"{path}: parser returned {len(db.entries)} entries but the file "
            f"contains {len(keys)}; entries were dropped."
        )
    out: list[BibEntry] = []
    for i, e in enumerate(db.entries):
        fields = {k.lower(): _scalar(v) for k, v in e.items()
                  if k not in ("ID", "ENTRYTYPE")}
        fields = {k: re.sub(r"\s+", " ", v).strip() for k, v in fields.items()}
        for k in TEXT_FIELDS:
            if fields.get(k):
                # Some records carry HTML entities verbatim (e.g. the journal
                # "Alimentary Pharmacology &amp; Therapeutics").
                fields[k] = normalize_glyphs(delatex(_html.unescape(fields[k])))
        out.append(BibEntry(key=e["ID"], etype=e["ENTRYTYPE"].lower(),
                            fields=fields, order=i, source=source))
    return out


DEFAULT_BIB_FILES = {
    "publications": "publications.bib",
    "preprints": "preprints.bib",
    "reviews_ja": "japanese_reviews.bib",
}


class Bibliography:
    """The three curated .bib files.  Scratch files are never globbed in."""

    def __init__(self, groups: dict[str, list[BibEntry]]):
        self.groups = groups
        self.by_key: dict[str, BibEntry] = {}
        for entries in groups.values():
            for e in entries:
                self.by_key[e.key] = e

    @classmethod
    def load(cls, bib_dir: Path,
             files: dict[str, str] | None = None) -> "Bibliography":
        files = files or DEFAULT_BIB_FILES
        groups = {name: load_bib(Path(bib_dir) / fn, name)
                  for name, fn in files.items()}
        allk = [e.key for g in groups.values() for e in g]
        dups = sorted(k for k, n in Counter(allk).items() if n > 1)
        if dups:
            raise DuplicateKeyError(
                f"duplicate bibkey(s) across bibliographies: {dups}")
        return cls(groups)

    @property
    def all(self) -> list[BibEntry]:
        return [e for g in self.groups.values() for e in g]

    def selected(self) -> list[BibEntry]:
        return [e for e in self.groups.get("publications", []) if e.is_selected]
