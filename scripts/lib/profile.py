"""Loaders for the authored YAML inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .cite import SelfName
from .report import Loc, Report

LANGUAGES = ("en", "ja")
VARIANTS = ("short", "full")
#: "both" = the selected subset inline plus the full list at the end
PUB_MODES = ("none", "selected", "full", "both")


def _load(path: Path, rep: Report):
    if not path.exists():
        rep.error("E-MISSING-FILE", Loc(path.name), f"{path} not found")
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        rep.error("E-YAML", Loc(path.name), f"cannot parse: {e}")
        return None


@dataclass
class Profile:
    data: dict

    def get(self, *path, default=None):
        cur = self.data
        for p in path:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(p)
            if cur is None:
                return default
        return cur

    def text(self, field: str, lang: str) -> str | None:
        return self.get(field, lang)

    @property
    def self_name(self) -> SelfName:
        aliases = self.get("self_bib_aliases", default=[])
        if aliases:
            a = aliases[0]
            return SelfName(a["family"], a["given_initial"])
        return SelfName("Namba", "S")

    @property
    def name_en(self) -> str:
        return self.get("name", "en", default="")

    @property
    def degrees_en(self) -> list[str]:
        return self.get("degrees", "en", default=[]) or []


@dataclass
class CVProfile:
    name: str
    language: str
    variant: str
    publications: str
    publish_to_site: bool
    output: str
    drop_sections: frozenset = frozenset()
    extra_sections: frozenset = frozenset()

    @property
    def visibility_column(self) -> str | None:
        """Column gating which records appear, or None to show every record.

        `variant: full` is the personal reference copy and is unfiltered,
        which is why there is no visible_cv_full column in the workbook.
        """
        return None if self.variant == "full" else "visible_cv_short"

    @property
    def target(self) -> str:
        """Which show_* gate set applies to per-field values."""
        return f"cv_{self.variant}"


def load_profile(path: Path, rep: Report) -> Profile:
    return Profile(_load(path, rep) or {})


def load_cv_profiles(path: Path, rep: Report) -> dict[str, CVProfile]:
    raw = _load(path, rep) or {}
    out: dict[str, CVProfile] = {}
    for name, d in (raw.get("profiles") or {}).items():
        loc = Loc(path.name, None, None, name)
        lang = d.get("language")
        variant = d.get("variant")
        pubs = d.get("publications")
        if lang not in LANGUAGES:
            rep.error("E-BAD-PROFILE", loc,
                      f"language must be one of {LANGUAGES}, got {lang!r}")
        if variant not in VARIANTS:
            rep.error("E-BAD-PROFILE", loc,
                      f"variant must be one of {VARIANTS}, got {variant!r}")
        if pubs not in PUB_MODES:
            rep.error("E-BAD-PROFILE", loc,
                      f"publications must be one of {PUB_MODES}, got {pubs!r}")
        out[name] = CVProfile(
            name=name, language=lang, variant=variant, publications=pubs,
            publish_to_site=bool(d.get("publish_to_site")),
            output=d.get("output") or f"CV_{name}",
            drop_sections=frozenset(d.get("drop_sections") or ()),
            extra_sections=frozenset(d.get("extra_sections") or ()),
        )
    if not out:
        rep.error("E-BAD-PROFILE", Loc(path.name), "no profiles defined")
    return out


def load_featured(path: Path, rep: Report) -> list[dict]:
    raw = _load(path, rep) or []
    if not isinstance(raw, list):
        rep.error("E-YAML", Loc(path.name), "expected a list of entries")
        return []
    out = []
    for i, item in enumerate(raw):
        loc = Loc(path.name, None, i + 1)
        if not isinstance(item, dict) or not item.get("bibkey"):
            rep.error("E-FEATURED-KEY", loc, "entry has no bibkey")
            continue
        out.append(item)
    out.sort(key=lambda d: (d.get("order", 10 ** 6), d["bibkey"]))
    return out
