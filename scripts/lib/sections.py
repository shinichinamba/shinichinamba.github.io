"""Assemble a Document from the master data, the profile and the bibliography."""

from __future__ import annotations

from pathlib import Path

import yaml

from .bib import Bibliography, BibEntry
from .cite import CV_STYLE, CiteStyle, SelfName, cite_runs
from .display import join
from .formatters import FORMATTERS
from .model import Document, Entry, Run, Section
from .profile import CVProfile, Profile
from .records import Dataset, sort_records

CONFIG = Path(__file__).resolve().parents[1] / "cv_sections.yml"

PUB_SUBSECTIONS = [
    ("preprints", {"en": "Preprints", "ja": "プレプリント"}),
    ("publications", {"en": "Peer-Reviewed Publications",
                      "ja": "査読付き学術論文"}),
    ("reviews_ja", {"en": "Reviews (in Japanese)", "ja": "総説（日本語）"}),
]

#: Labels for the Public Profiles section.
PROFILE_LABELS = {
    "website": {"en": "Website", "ja": "ウェブサイト"},
    "orcid": {"en": "ORCID", "ja": "ORCID"},
    "researchmap": {"en": "researchmap", "ja": "researchmap"},
    "google_scholar": {"en": "Google Scholar", "ja": "Google Scholar"},
    "github": {"en": "GitHub", "ja": "GitHub"},
}
PROFILE_ORDER = ("website", "orcid", "researchmap", "google_scholar")


def load_config(path: Path = CONFIG) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------


#: Role of each header line, consumed by the renderer to pick a font size.
HEADER_ROLES = ("furigana", "name", "subtitle", "contact")


def header_section(profile: Profile, lang: str
                   ) -> tuple[Section, list[str]]:
    """Return the header section and a parallel list of line roles."""
    entries: list[Entry] = []
    roles: list[str] = []

    def add(entry: Entry, role: str) -> None:
        entries.append(entry)
        roles.append(role)

    name = profile.get("name", lang) or profile.get("name", "en")
    degrees = profile.get("degrees", "en", default=[]) or []

    if lang == "ja":
        reading = profile.get("name", "reading_ja")
        if reading:
            # Furigana sits above the name in small type, as on a Japanese
            # rirekisho. Putting it inline at name size overflows the column
            # once the portrait is beside it.
            add(Entry(body=(Run(f"（{reading}）"),)), "furigana")
        add(Entry(body=(Run(name, bold=True),)), "name")
        latin = profile.get("name", "en")
        if latin:
            suffix = ", ".join(degrees)
            add(Entry(body=(Run(f"{latin}, {suffix}" if suffix else latin),)),
                "subtitle")
    else:
        suffix = ", ".join(degrees)
        add(Entry(body=(Run(f"{name}, {suffix}" if suffix else name,
                            bold=True),)), "name")

    pos = profile.get("current_position", lang)
    if pos:
        add(Entry(body=(Run(pos),)), "subtitle")

    email = profile.get("contact", "email")
    if email:
        add(Entry(body=(Run(email, href=f"mailto:{email}"),)), "contact")
    # Online identifiers now live in the Public Profiles section at the end,
    # so the header carries only the postal contact details.
    address = profile.get("contact", "address", lang) or \
        profile.get("contact", "address", "en")
    if address:
        for line in str(address).splitlines():
            if line.strip():
                add(Entry(body=(Run(line.strip()),)), "contact")

    return Section(key="header", heading=None, kind="header",
                   entries=tuple(entries)), roles


def public_profiles_section(profile: Profile, spec: dict, lang: str,
                            plain_keys: set[str]) -> Section | None:
    """Website / ORCID / researchmap, listed at the end of the CV.

    Entries named in ``plain_keys`` are written as literal URLs with no
    hyperlink, so the identifier stays readable on paper.
    """
    entries: list[Entry] = []
    for key in PROFILE_ORDER:
        url = profile.get("links", key)
        if not url:
            continue
        label = PROFILE_LABELS[key][lang]
        runs = [Run(f"{label}: ")]
        if key in plain_keys:
            runs.append(Run(str(url)))
        else:
            runs.append(Run(str(url), href=str(url)))
        entries.append(Entry(body=tuple(runs)))
    if not entries:
        return None
    return Section(key="public_profiles", heading=spec["heading"][lang],
                   kind="plainlist", entries=tuple(entries))


def paragraph_section(profile: Profile, spec: dict, key: str,
                      lang: str) -> Section | None:
    field = spec["source"].get("field")
    text = profile.get(field, lang) or profile.get(field, "en")
    if not text:
        return None
    # A trailing "など" / "..." reads as padding on a CV. Stripped here rather
    # than in profile.yml so the website keeps its own wording.
    for filler in spec.get("strip_trailing") or ():
        stripped = str(text).rstrip()
        if stripped.endswith(filler):
            text = stripped[: -len(filler)].rstrip(" 　/・,、")
    return Section(key=key, heading=spec["heading"][lang], kind="paragraph",
                   entries=(Entry(body=(Run(text),)),))


def sheet_section(ds: Dataset, spec: dict, key: str, lang: str,
                  cvp: CVProfile, extra_rows=None,
                  visibility: str | None = None,
                  target: str | None = None,
                  never_show: tuple = ()) -> Section | None:
    """``visibility`` names the gating column; None means show every row."""
    rows = [r for r in sort_records(ds)
            if visibility is None or bool(r.values.get(visibility))]
    items = [(ds, r) for r in rows]
    for eds, erow in (extra_rows or []):
        items.append((eds, erow))
    if not items:
        return None
    # merged sections re-sort across datasets by the same key
    if extra_rows:
        from .records import record_sort_seq
        items.sort(key=lambda p: record_sort_seq(p[0], p[1]))
    opts = {"target": target or cvp.target, "never_show": never_show}
    entries = []
    for d, r in items:
        fmt = FORMATTERS[SECTION_FORMATTER[d.key]]
        entries.append(fmt(d, r, lang, opts))
    return Section(key=key, heading=spec["heading"][lang], kind="entries",
                   entries=tuple(entries))


SECTION_FORMATTER = {
    "appointments": "appointment", "clinical_training": "clinical",
    "education": "education", "awards": "award", "fellowships": "fellowship",
    "grants": "grant", "teaching": "teaching", "invited_talks": "talk",
    "reviewing": "reviewing", "committees": "committee", "patents": "patent",
    "memberships": "membership",
}


def _numbered(entries_src: list[BibEntry], me: SelfName, start: int = 1,
              *, style: CiteStyle = CV_STYLE) -> tuple[Entry, ...]:
    out = []
    for i, e in enumerate(entries_src, start=start):
        runs = [Run(f"{i}. ")] + cite_runs(e, me, style=style)
        out.append(Entry(body=tuple(runs)))
    return tuple(out)


def selected_publications_section(bib: Bibliography, spec: dict, lang: str,
                                  profile: Profile, style: CiteStyle
                                  ) -> Section | None:
    sel = bib.selected()
    if not sel:
        return None
    total = len(bib.groups.get("publications", []))
    if lang == "ja":
        note_text = (f"査読付き論文 {total} 編のうち主要な {len(sel)} 編。"
                     f"全リストは本CV末尾に記載。")
    else:
        note_text = (f"Selected {len(sel)} of {total} peer-reviewed "
                     f"publications; the complete list is at the end of this "
                     f"CV.")
    # The legend and the count are both wanted: the markers mean nothing
    # without the legend, and the count says this is not the whole list.
    # A visible separator: without one the legend and the count run together
    # ("...corresponding author Selected 6 of 40...").
    legend = _legend(sel, lang, style)
    sep = (Run("  ·  ", small=True),) if legend else ()
    note = legend + sep + (Run(note_text, small=True),)
    return Section(key="publications", heading=spec["heading"][lang],
                   kind="numbered",
                   entries=_numbered(sel, profile.self_name, style=style),
                   note=note)


def full_publications_section(bib: Bibliography, spec: dict, lang: str,
                              profile: Profile, style: CiteStyle
                              ) -> Section | None:
    me = profile.self_name
    subs: list[Section] = []
    for group, titles in PUB_SUBSECTIONS:
        items = bib.groups.get(group, [])
        if not items:
            continue
        subs.append(Section(key=f"publications_{group}",
                            heading=titles[lang], kind="numbered",
                            entries=_numbered(items, me, style=style)))
    if not subs:
        return None
    return Section(key="publications_full", heading=spec["heading"][lang],
                   kind="numbered", entries=(), subsections=tuple(subs),
                   note=_legend(bib.all, lang, style))


def _legend(entries_src, lang: str, style: CiteStyle) -> tuple[Run, ...]:
    """Show the marker legend only when a displayed entry actually uses one."""
    if any(a.eq or a.corr for e in entries_src for a in e.authors):
        return (Run(style.legend(lang), small=True),)
    return ()


# --------------------------------------------------------------------------


def divider_section(spec: dict, lang: str) -> Section:
    return Section(key="full_divider", heading=spec["heading"][lang],
                   kind="divider")


def build_document(master: dict[str, Dataset], profile: Profile,
                   bib: Bibliography, cvp: CVProfile,
                   config: dict | None = None) -> Document:
    cfg = config or load_config()
    specs = cfg["sections"]
    blocks = cfg["blocks"]
    opts = cfg.get("options", {})
    merge_clinical = (cvp.language == "ja"
                      and opts.get("ja_merge_clinical_into_appointments"))
    plain_keys = set(opts.get("plain_text_links") or ())
    never_show = tuple(opts.get("never_show") or ())
    photo = (opts.get("photo") or {}).get(cvp.language)

    doc = Document(language=cvp.language, variant=cvp.variant,
                   profile_name=cvp.name,
                   meta={"generator": "scripts/build_cv.py",
                         "photo": photo, "record_ids": []})

    for block, orders in blocks.items():
        order = orders[cvp.language]
        # None for the personal full copy, which shows every record.
        visibility = cvp.visibility_column

        for key in order:
            spec = specs.get(key)
            if not spec:
                continue
            if key in cvp.drop_sections:
                continue
            if not spec.get("enabled") and key not in cvp.extra_sections:
                continue
            if key == "clinical_training" and merge_clinical:
                continue

            src = spec["source"]
            kind = src["kind"]
            out_key = key
            section: Section | None = None

            if kind == "divider":
                section = divider_section(spec, cvp.language)
            elif kind == "profile":
                fmt = spec["formatter"]
                if fmt == "header":
                    section, roles = header_section(profile, cvp.language)
                    doc.meta["header_roles"] = roles
                elif fmt == "public_profiles":
                    section = public_profiles_section(profile, spec,
                                                      cvp.language, plain_keys)
                else:
                    section = paragraph_section(profile, spec, out_key,
                                                cvp.language)
            elif kind == "bibliography":
                if cvp.publications == "none":
                    section = None
                elif src.get("mode") == "selected":
                    section = selected_publications_section(
                        bib, spec, cvp.language, profile, CV_STYLE)
                else:
                    section = full_publications_section(
                        bib, spec, cvp.language, profile, CV_STYLE)
            else:
                ds = master[src["sheet"]]
                extra = None
                if key == "appointments" and merge_clinical:
                    cds = master["clinical_training"]
                    extra = [(cds, r) for r in sort_records(cds)
                             if visibility is None
                             or bool(r.values.get(visibility))]
                # The full block reveals the cv_full-gated values (amounts,
                # grant numbers); the short block keeps the cv_short view.
                section = sheet_section(ds, spec, out_key, cvp.language, cvp,
                                        extra, visibility,
                                        target=cvp.target,
                                        never_show=never_show)
                if visibility:
                    doc.meta["record_ids"] += [
                        r.id for r in ds.records
                        if bool(r.values.get(visibility))]
                    doc.meta["record_ids"] += [r.id for _d, r in (extra or [])]

            if section is None:
                continue
            if section.kind != "divider" and not (section.entries
                                                  or section.subsections):
                continue
            doc.sections.append(
                section if section.key == out_key
                else Section(out_key, section.heading, section.kind,
                             section.entries, section.subsections,
                             section.note))
    # A divider with nothing after it would be a dangling page break.
    while doc.sections and doc.sections[-1].kind == "divider":
        doc.sections.pop()
    return doc
