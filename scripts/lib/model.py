"""Document intermediate representation.

Both renderers (DOCX, and the optional HTML/Chrome path) consume this IR and
never look at the spreadsheet or the .bib files.  Every string here is already
fully formatted and every emphasis is already expressed as inline runs, so the
renderers only decide geometry and typeface -- never content.  That is what
keeps the DOCX and the PDF from drifting apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Run:
    """An inline span of text with optional emphasis and hyperlink."""

    text: str
    bold: bool = False
    italic: bool = False
    href: str | None = None
    small: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):  # pragma: no cover - guard
            raise TypeError(f"Run.text must be str, got {type(self.text)!r}")


def plain(runs: list[Run]) -> str:
    """Flatten runs to their text, for tests and for diagnostics."""
    return "".join(r.text for r in runs)


@dataclass(frozen=True)
class Entry:
    """One line item: a left-hand date column plus body, with optional detail."""

    date: tuple[Run, ...] = ()
    body: tuple[Run, ...] = ()
    detail: tuple[Run, ...] = ()


@dataclass(frozen=True)
class Section:
    key: str
    heading: str | None
    kind: Literal["entries", "paragraph", "numbered", "header"] = "entries"
    entries: tuple[Entry, ...] = ()
    subsections: tuple["Section", ...] = ()
    note: tuple[Run, ...] = ()


@dataclass
class Document:
    language: Literal["en", "ja"]
    variant: Literal["short", "full"]
    profile_name: str
    sections: list[Section] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
