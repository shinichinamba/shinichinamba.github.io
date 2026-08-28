"""Nature-style citation rendering, matching what the website shows.

The website's output is produced by ``_bibliography/custom.csl`` (a modified
Nature style) and then post-processed by ``_plugins/jekyll_scholar.rb``.  The
observable result, which this module reproduces, is:

    Namba, S., Sonehara, K. ... Title. Journal 83, 20-27 (2022).

with these specifics, all verified against docs/publications/index.html:

* names render as ``Family, I.`` with ``initialize-with=". "``;
* two authors are joined with ``&`` and no serial comma
  (``delimiter-precedes-last="never"``);
* more than six authors collapse to six plus *et al.*, and when the author's
  own name would be truncated away it is pulled back in after a ``, ..., ``
  gap so it is always visible;
* journal names are NOT abbreviated -- custom.csl asks for ``form="short"``
  but citeproc-ruby ships no abbreviation database, so the full name is what
  actually renders;
* the volume is bold and carries its trailing comma, and is omitted entirely
  when absent;
* the title carries the DOI hyperlink;
* the author's own name is bold, and the ``*`` / ``**`` markers are inside the
  bold span (the site's regex is ``\\**Namba, S``).
"""

from __future__ import annotations

import html as _html
import re
import unicodedata
from dataclasses import dataclass

from .bib import Author, BibEntry
from .model import Run

ET_AL_LIMIT = 6


@dataclass(frozen=True)
class CiteStyle:
    """How names and contribution markers are written.

    The website and the CV deliberately differ: the site is fixed by
    custom.csl + _plugins/jekyll_scholar.rb and must not change, while the CV
    uses the compact "Namba S" form and a distinct co-corresponding mark.
    """

    name_comma: bool = True        # "Namba, S." vs "Namba S"
    initial_periods: bool = True   # "Y. N."     vs "YN"
    eq_marker: str = "*"
    corr_marker: str = "**"
    #: "prefix" -> *Namba S (what the website does), "suffix" -> Namba S*
    marker_position: str = "prefix"

    def legend(self, lang: str) -> str:
        if lang == "ja":
            return (f"{self.eq_marker} 共同筆頭著者、"
                    f"{self.corr_marker} 責任著者（共同責任著者を含む）")
        return (f"{self.eq_marker} equal contribution; "
                f"{self.corr_marker} (co-)corresponding author")


#: Exactly what the built site renders. Used by the parity test; do not change.
SITE_STYLE = CiteStyle()

#: The CV house style.
CV_STYLE = CiteStyle(name_comma=False, initial_periods=False,
                     eq_marker="*", corr_marker="\u266f",
                     marker_position="suffix")


@dataclass(frozen=True)
class SelfName:
    family: str
    given_initial: str

    @property
    def key(self) -> tuple[str, str]:
        return (_fold(self.family), self.given_initial.lower())


def _fold(s: str) -> str:
    return (unicodedata.normalize("NFKD", s)
            .encode("ascii", "ignore").decode("ascii").lower())


def is_self(a: Author, me: SelfName) -> bool:
    fam = _fold(a.family)
    giv = _fold(a.given)
    return (fam, giv[:1]) == me.key


def collapse_authors(authors: list[Author], me: SelfName,
                     limit: int = ET_AL_LIMIT
                     ) -> tuple[list[Author], bool, int | None]:
    """Return ``(shown, truncated, gap_index)``.

    ``gap_index`` is the position *before* which a ``, ..., `` separator is
    rendered, or None when the shown authors are a plain prefix.
    """
    # The site truncates at EIGHT or more authors, not seven.  Its et-al helper
    # splits the rendered string on ".," and bails out when it sees <= 6 chunks;
    # because the final separator is " & " rather than "., ", an N-author list
    # yields only N-1 chunks, so a 7-author list slips through untruncated.
    if len(authors) <= limit + 1:
        return list(authors), False, None
    head = authors[:limit]
    if any(is_self(a, me) for a in head):
        return head, True, None
    idx = next((i for i, a in enumerate(authors) if is_self(a, me)), None)
    if idx is None:
        return head, True, None
    return authors[: limit - 1] + [authors[idx]], True, limit - 1


# --------------------------------------------------------------------------
# titles: the corpus contains raw HTML italics (e.g. <i>Helicobacter pylori</i>)
# --------------------------------------------------------------------------

_TAG = re.compile(r"</?(i|em|b|strong|sub|sup)\s*>", re.I)


def title_runs(title: str, href: str | None) -> list[Run]:
    """Split a title into runs, honouring inline <i>/<em> emphasis."""
    out: list[Run] = []
    italic = False
    pos = 0
    for m in _TAG.finditer(title):
        chunk = title[pos:m.start()]
        if chunk:
            out.append(Run(_html.unescape(chunk), italic=italic, href=href))
        tag = m.group(1).lower()
        if tag in ("i", "em"):
            italic = not m.group(0).startswith("</")
        pos = m.end()
    tail = title[pos:]
    if tail:
        out.append(Run(_html.unescape(tail), italic=italic, href=href))
    return out or [Run(_html.unescape(title), href=href)]


def normalize_pages(pages: str) -> str:
    """``1110-1112`` -> ``1110–1112`` (custom.csl renders an en dash)."""
    return re.sub(r"\s*[-‐-―]+\s*", "–", pages.strip())


def journal_name(e: BibEntry) -> str:
    return e.get("journal") or e.get("booktitle") or ""


def name_of(a: Author, style: CiteStyle) -> str:
    """``Namba, S`` (site) or ``Namba S`` (CV); the caller adds any period."""
    initials = a.initials if style.initial_periods else \
        a.initials.replace(".", "").replace("-", "").replace(" ", "")
    initials = initials.rstrip(".")
    if not initials:
        return a.family
    return f"{a.family}, {initials}" if style.name_comma \
        else f"{a.family} {initials}"


def marker_of(a: Author, style: CiteStyle) -> str:
    if a.corr:
        return style.corr_marker
    return style.eq_marker if a.eq else ""


def author_runs(e: BibEntry, me: SelfName,
                style: CiteStyle = SITE_STYLE) -> list[Run]:
    shown, truncated, gap = collapse_authors(e.authors, me)
    runs: list[Run] = []
    n = len(shown)
    for i, a in enumerate(shown):
        if i:
            if gap is not None and i == gap:
                runs.append(Run(", ..., "))
            elif not truncated and i == n - 1:
                runs.append(Run(" & "))      # `and="symbol"`, no serial comma
            else:
                runs.append(Run(", "))
        name, mark = name_of(a, style), marker_of(a, style)
        label = f"{name}{mark}" if style.marker_position == "suffix" \
            else f"{mark}{name}"
        runs.append(Run(label, bold=is_self(a, me)))
        if style.initial_periods:
            runs.append(Run("."))            # the period of the final initial
    if truncated:
        runs.append(Run(" "))
        runs.append(Run("et al.", italic=True))
    return runs


def cite_runs(e: BibEntry, me: SelfName, *, title_override: str | None = None,
              style: CiteStyle = SITE_STYLE) -> list[Run]:
    """Full citation for one entry, as inline runs."""
    runs = author_runs(e, me, style)
    # The author block must end in a period before the title. With the
    # site style that period is already there (it belongs to the last
    # initial); with the CV style "Okada Y" needs one added.
    if not "".join(r.text for r in runs).rstrip().endswith("."):
        runs.append(Run("."))
    runs.append(Run(" "))

    title = (title_override or e.get("title") or "").strip().rstrip(".")
    runs += title_runs(title + ".", e.doi_url)

    jn = journal_name(e)
    if jn:
        runs.append(Run(" "))
        runs.append(Run(jn, italic=True))

    vol = e.get("volume")
    if vol:
        runs.append(Run(" "))
        runs.append(Run(f"{vol},", bold=True))

    pages = e.get("pages")
    if pages:
        runs.append(Run(f" {normalize_pages(pages)}"))

    runs.append(Run(f" ({e.year})."))
    return runs
