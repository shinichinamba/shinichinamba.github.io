"""Per-dataset entry formatters, one per sheet, in both languages.

Every formatter must degrade cleanly when an optional field is blank: no
stray ", ," and no dangling parentheses.  ``join`` drops empties, and
parenthesised groups are only built when the group is non-empty.
"""

from __future__ import annotations

from typing import Callable

from .dates import format_range, is_ongoing
from .display import format_amount, join, quote
from .model import Entry, Run
from .records import Dataset, Record
from .schema import no_fallback_columns

FORMATTERS: dict[str, Callable] = {}


def formatter(name: str):
    def deco(fn):
        FORMATTERS[name] = fn
        return fn
    return deco


def _bi(ds: Dataset, r: Record, field: str, lang: str) -> str | None:
    """The value for ``lang``, falling back to the other language.

    Columns declared ``fallback=False`` skip the fallback: a blank there is a
    deliberate omission, not a missing translation.
    """
    v = r.values.get(f"{field}_{lang}")
    if v:
        return str(v)
    if field in no_fallback_columns(ds.sheet):
        return None
    other = r.values.get(f"{field}_{'en' if lang == 'ja' else 'ja'}")
    return str(other) if other else None


def _date_runs(ds: Dataset, r: Record, lang: str) -> tuple[Run, ...]:
    primary = ds.primary_date(r)
    start = r.values.get("start_date", primary) or primary
    end = r.values.get("end_date")
    # Only sheets that record a range can be ongoing. On a single-date sheet
    # such as awards the absent end date means "not a range", not "still
    # running", and an open dash there would be wrong.
    ranged = any(c.name == "end_date" for c in ds.sheet.columns)
    text = format_range(start, end, ranged and is_ongoing(end), lang)
    return (Run(text),) if text else ()


def _entry(ds, r, lang, body: str, detail: str | None = None) -> Entry:
    return Entry(date=_date_runs(ds, r, lang),
                 body=(Run(body),) if body else (),
                 detail=(Run(detail),) if detail else ())


# --------------------------------------------------------------------------


@formatter("appointment")
def fmt_appointment(ds, r, lang, opts=None):
    if lang == "ja":
        body = join([_bi(ds, r, "institution", lang), _bi(ds, r, "department", lang),
                     _bi(ds, r, "position", lang)], lang)
    else:
        body = join([_bi(ds, r, "position", lang), _bi(ds, r, "department", lang),
                     _bi(ds, r, "institution", lang), _bi(ds, r, "location", lang)], lang)
    return _entry(ds, r, lang, body)


@formatter("clinical")
def fmt_clinical(ds, r, lang, opts=None):
    if lang == "ja":
        body = join([_bi(ds, r, "institution", lang), _bi(ds, r, "department", lang),
                     _bi(ds, r, "position", lang)], lang)
    else:
        body = join([_bi(ds, r, "position", lang), _bi(ds, r, "department", lang),
                     _bi(ds, r, "institution", lang), _bi(ds, r, "location", lang)], lang)
    return _entry(ds, r, lang, body)


@formatter("education")
def fmt_education(ds, r, lang, opts=None):
    if lang == "ja":
        body = join([_bi(ds, r, "institution", lang), _bi(ds, r, "department", lang),
                     _bi(ds, r, "field", lang), _bi(ds, r, "degree", lang)], lang)
    else:
        body = join([_bi(ds, r, "degree", lang), _bi(ds, r, "field", lang),
                     _bi(ds, r, "department", lang), _bi(ds, r, "institution", lang),
                     _bi(ds, r, "location", lang)], lang)
    advisor = _bi(ds, r, "advisor", lang)
    detail = None
    if advisor:
        detail = f"指導教員：{advisor}" if lang == "ja" else f"Advisor: {advisor}"
    return _entry(ds, r, lang, body, detail)


@formatter("award")
def fmt_award(ds, r, lang, opts=None):
    order = ["organization", "award"] if lang == "ja" else ["award", "organization"]
    body = join([_bi(ds, r, f, lang) for f in order], lang)
    return _entry(ds, r, lang, body, _bi(ds, r, "description", lang))


@formatter("fellowship")
def fmt_fellowship(ds, r, lang, opts=None):
    order = (["organization", "fellowship"] if lang == "ja"
             else ["fellowship", "organization"])
    body = join([_bi(ds, r, f, lang) for f in order], lang)
    return _entry(ds, r, lang, body, _bi(ds, r, "description", lang))


@formatter("grant")
def fmt_grant(ds, r, lang, opts=None):
    target = (opts or {}).get("target", "cv_full")
    never = set((opts or {}).get("never_show") or ())
    head = join([_bi(ds, r, "agency", lang), _bi(ds, r, "program", lang)], lang)
    title = _bi(ds, r, "title", lang)
    if title:
        head = (head + quote(title, lang) if lang == "ja"
                else join([head, quote(title, lang)], lang))

    paren: list[str] = []
    if ("grant_number" not in never
            and r.gate("grant_number", target)
            and r.values.get("grant_number")):
        n = r.values["grant_number"]
        paren.append(f"課題番号 {n}" if lang == "ja" else f"Grant No. {n}")
    role = r.values.get("role")
    if role:
        paren.append({"PI": "研究代表者", "Co-I": "研究分担者",
                      "Collaborator": "連携研究者",
                      "Other": "その他"}.get(role, role) if lang == "ja" else role)
    if "amount" not in never and r.gate("amount", target) \
            and r.values.get("amount_jpy"):
        amt = format_amount(r.values["amount_jpy"],
                            r.values.get("amount_type"), lang,
                            parenthesize=False)
        if amt:
            paren.append(amt)
    if paren:
        sep = "、" if lang == "ja" else "; "
        head += ("（" + sep.join(paren) + "）" if lang == "ja"
                 else " (" + sep.join(paren) + ")")
    return _entry(ds, r, lang, head)


@formatter("teaching")
def fmt_teaching(ds, r, lang, opts=None):
    if lang == "ja":
        body = join([_bi(ds, r, "course", lang), _bi(ds, r, "institution", lang),
                     _bi(ds, r, "school", lang), _bi(ds, r, "role", lang)], lang)
    else:
        body = join([_bi(ds, r, "course", lang), _bi(ds, r, "role", lang),
                     _bi(ds, r, "school", lang), _bi(ds, r, "institution", lang)], lang)
    return _entry(ds, r, lang, body)


@formatter("talk")
def fmt_talk(ds, r, lang, opts=None):
    title, event = _bi(ds, r, "title", lang), _bi(ds, r, "event", lang)
    loc = _bi(ds, r, "location", lang)
    if lang == "ja":
        body = join([event, f"（{loc}）" if loc else None], lang)
        body = (body + quote(title, lang)) if title else body
    else:
        body = join([quote(title, lang) if title else None, event, loc], lang)
    ttype = r.values.get("talk_type")
    # Only a keynote is called out. "symposium" used to be labelled too, but
    # every talk in the conference section is one, so the tag said nothing.
    if ttype == "keynote":
        label = ("Keynote", "基調講演")
        body += f"（{label[1]}）" if lang == "ja" else f" ({label[0]})"
    return _entry(ds, r, lang, body)


@formatter("membership")
def fmt_membership(ds, r, lang, opts=None):
    body = _bi(ds, r, "organization", lang) or ""
    mtype = _bi(ds, r, "membership_type", lang)
    if mtype:
        body += f"（{mtype}）" if lang == "ja" else f" ({mtype})"
    return _entry(ds, r, lang, body)


@formatter("reviewing")
def fmt_reviewing(ds, r, lang, opts=None):
    body = join([_bi(ds, r, "journal_or_program", lang),
                 _bi(ds, r, "organization", lang)], lang)
    n = r.values.get("count")
    if n:
        body += f"（{n}件）" if lang == "ja" else f" ({n})"
    return _entry(ds, r, lang, body)


@formatter("committee")
def fmt_committee(ds, r, lang, opts=None):
    order = (["organization", "committee", "role"] if lang == "ja"
             else ["role", "committee", "organization"])
    return _entry(ds, r, lang, join([_bi(ds, r, f, lang) for f in order], lang))


@formatter("patent")
def fmt_patent(ds, r, lang, opts=None):
    title = _bi(ds, r, "title", lang)
    body = quote(title, lang) if title else ""
    bits = [r.values.get("application_number") or r.values.get("patent_number"),
            r.values.get("status")]
    bits = [b for b in bits if b]
    if bits:
        body += ("（" + "、".join(map(str, bits)) + "）" if lang == "ja"
                 else " (" + ", ".join(map(str, bits)) + ")")
    return _entry(ds, r, lang, body)
