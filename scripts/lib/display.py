"""Shared EN/JA string composition.

Anything that would otherwise force Liquid or a renderer to make a formatting
decision is resolved here, once, in Python.
"""

from __future__ import annotations

IDEOGRAPHIC_SPACE = "　"

AMOUNT_TYPE_LABEL = {
    "total_project": {"en": "total", "ja": "総額"},
    "direct_cost": {"en": "direct cost", "ja": "直接経費"},
    "personal_allocation": {"en": "personal allocation", "ja": "分担額"},
    "unknown": {"en": None, "ja": None},
}


def join(parts, lang: str) -> str:
    """Join non-empty parts with the separator idiomatic for the language."""
    sep = IDEOGRAPHIC_SPACE if lang == "ja" else ", "
    return sep.join(p for p in parts if p)


def quote(text: str, lang: str) -> str:
    return f"「{text}」" if lang == "ja" else f"“{text}”"


def format_amount(amount_jpy: int | None, amount_type: str | None,
                  lang: str, *, parenthesize: bool = True) -> str | None:
    """``¥4,550,000 (total)`` / ``4,550,000円（総額）``.

    Pass ``parenthesize=False`` when the caller is already building a
    parenthesised group, so the qualifier does not nest brackets.
    """
    if not amount_jpy:
        return None
    label = AMOUNT_TYPE_LABEL.get(amount_type or "unknown", {}).get(lang)
    base = f"{amount_jpy:,}円" if lang == "ja" else f"¥{amount_jpy:,}"
    if not label:
        return base
    if not parenthesize:
        return f"{base} {label}" if lang == "en" else f"{base}（{label}）"
    return f"{base} ({label})" if lang == "en" else f"{base}（{label}）"


def pick(value, lang: str):
    """Bilingual dict -> the requested language, falling back to English."""
    if not isinstance(value, dict):
        return value
    return value.get(lang) or value.get("en") or value.get("ja")
