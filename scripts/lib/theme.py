"""All CV geometry and typography in one place.

Both the DOCX renderer and the optional HTML/Chrome renderer read these
constants, so the two cannot drift apart on layout.
"""

from __future__ import annotations

# page (mm)
PAGE = {"width": 210.0, "height": 297.0,
        "margin_top": 20.0, "margin_bottom": 18.0,
        "margin_left": 18.0, "margin_right": 18.0}

#: Width of the left-hand date column (mm).  It must clear the WIDEST date a
#: section can produce, otherwise the tab overshoots to the next default stop
#: and that one row's body loses its alignment.  The widest cases are
#: "Oct 2023 - Mar 2025" in English and "2025/12/19" in Japanese.
DATE_COL = {"en": 34.0, "ja": 30.0}

FONT = {
    "latin": "Times New Roman",
    #: Verified present on this machine via `fc-list :lang=ja family`.
    #: Pairs with Times New Roman (both serif) and is fontconfig's
    #: serif:lang=ja default, so LibreOffice embeds it without substitution.
    "cjk": "Hiragino Mincho ProN",
}

SIZE = {          # points
    "name": 20,
    "subtitle": 11,
    "contact": 9.5,
    "section": 12,
    "body": 10.5,
    "date": 9.5,
    "detail": 9.5,
    "note": 9,
}

SPACE = {         # points
    "after_name": 2,
    "after_header": 10,
    "before_section": 12,
    "after_section": 4,
    "after_entry": 3,
    "line": 1.15,
}

RULE_COLOR = "000000"
TEXT_COLOR = "000000"

#: Portrait beside the header block (Japanese CV only). Height is fixed and
#: the width follows the image's own aspect ratio, so a replacement photo
#: cannot distort.
PHOTO = {"height_mm": 34.0, "gap_mm": 4.0}

#: Page footer: fixed text on the left, page number on the right.
FOOTER = {
    "left": {"en": "S Namba | Curriculum Vitae",
             "ja": "S Namba | Curriculum Vitae"},
    "size": 8.5,
}
