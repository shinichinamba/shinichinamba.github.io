# data/ — authored inputs

Everything in this directory is written by a human. Everything under
`_data/cv/`, `build/` and `assets/cv/` is generated from it and must never be
hand-edited.

Regenerate after any change:

    make -C scripts all

## Editing rules

1. **Booleans are literal `TRUE` / `FALSE`.** Not `true`, not `1`, not `yes`,
   not a blank cell. Type them unquoted into a General-formatted cell.
2. **Date columns are formatted as Text.** Write `2024`, `2024-10` or
   `2024-10-15` and nothing else. The precision you write is the precision
   that is published, so do not pad a month-accurate fact out to a day.
   If Excel ever turns `2024-10` into a real date it will be read back as
   month precision, but you will get a warning; keep the columns as Text.
3. **`id` is permanent.** It is a machine key, not a label. Change the display
   text freely; never reuse or renumber an `id`.
4. **Do not duplicate bibliographic data.** Papers live in
   `_bibliography/*.bib`. `featured_publications.yml` refers to them by
   `bibkey` and adds only a summary.

## Visibility flags

`visible_web`, `visible_cv_short` and `visible_cv_full` select where a record
appears. `show_amount_*` and `show_grant_number_*` do the same for individual
grant values.

**These are not privacy controls.** The short CV is published at
`assets/cv/*.pdf`, so anything with `visible_cv_short = TRUE` and
`show_amount_cv_short = TRUE` is on the public web regardless of what
`visible_web` says. Use `visible_cv_full` for anything that should stay local.

## Validation

    python scripts/validate_cv_data.py

Exits non-zero on a real problem and refuses to generate anything. Use
`--explain-dates` to audit how every date cell was interpreted.
