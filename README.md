# shinichinamba.github.io

Personal site (Jekyll + So Simple) and CV, both generated from one set of
structured inputs.

## Where the data lives

| what | authored in | notes |
|---|---|---|
| Papers, preprints, Japanese reviews | `_bibliography/*.bib` | also drives the site via jekyll-scholar |
| Everything else on the CV | `data/cv_master.xlsx` | 12 sheets; see `data/README.md` |
| Prose, contact details, links | `data/profile.yml` | |
| Featured Research blurbs | `data/featured_publications.yml` | refers to papers by `bibkey` |
| CV profile definitions | `data/cv_profiles.yml` | |

**Generated — never edit by hand:** `_data/cv/*.yml`, `_data/profile.yml`,
`_data/featured_publications.yml`, `build/`, `assets/cv/*.pdf`, `docs/`.

## Updating

Edit the files under `data/` (or the `.bib` files), then:

```bash
make -C scripts all
```

That validates every input, regenerates `_data/cv/*.yml`, builds all four CV
profiles and copies the two public short PDFs into `assets/cv/`. If validation
fails nothing is written.

Then preview and deploy exactly as before:

```bash
bundle exec jekyll serve
```

```bash
rm -rf docs && cp -R _site docs && git add . && git commit -m '...' && git push origin master
```

`make -C scripts verify` additionally runs `jekyll build` and asserts that the
site really contains what it should — most importantly that Featured Research
rendered every entry, and that `data/` was not published.

## Commands

```bash
python scripts/validate_cv_data.py          # check inputs, generate nothing
python scripts/validate_cv_data.py --explain-dates   # audit date precision
python scripts/build_site_data.py           # regenerate _data/cv/*.yml
python scripts/build_cv.py --profile en
python scripts/build_cv.py --profile all --publish
python scripts/build_all.py --verify        # everything, with assertions
python -m unittest discover -s tests        # test suite
```

`build_cv.py` exit codes: `2` usage, `3` bad input data, `4` missing tool,
`5` publish-guard violation, `6` drift.

## CV outputs

One document per language, not a short/full choice. Each CV opens with the
short-CV body and closes with the complete publication list:

```
name · degrees · position · email · address      (JA also carries a portrait)
Personal Statements / Research Interests
Academic Appointments · Clinical Training · Education
Honors and Awards · Research Funding · Fellowships
Invited Talks · Teaching Experience
Selected Publications
Public Profiles           website, ORCID, researchmap
Publications              the complete list, last
```

| artifact | built to | committed | on the web |
|---|---|---|---|
| EN / JA PDF | `assets/cv/Shinichi_Namba_CV_{EN,JA}.pdf` | yes | **yes** |
| EN / JA DOCX | `build/cv/` | no | no |

A three-layer guard stops anything else reaching a published directory
(`assets/`, `_site/`, `docs/`); attempting it exits `5`.

House style, set in `scripts/lib/cite.py` and `scripts/cv_sections.yml`:

- Authors read `Namba S`, not `Namba, S.` The **website keeps its own style**
  (`Namba, S.` with `**`) — the two are deliberately independent.
- `*` marks equal contribution, `♯` marks a (co-)corresponding author.
- ORCID and researchmap are printed as literal URLs rather than hyperlinks.
- Every page carries `S Namba | Curriculum Vitae` bottom-left and the page
  number bottom-right.
- Memberships are held as data but not rendered on the CV.

## Requirements

- **Python 3.12+** with `openpyxl`, `PyYAML`, `python-docx`, `bibtexparser==1.4.4`

  ```bash
  python3 -m pip install openpyxl PyYAML python-docx "bibtexparser==1.4.4"
  ```

- **LibreOffice** for DOCX → PDF (`brew install --cask libreoffice`). Without
  it `build_cv.py` exits `4` with the fix; `--formats docx` skips PDFs.
- **poppler** for PDF verification (`brew install poppler`). Provides
  `pdffonts` / `pdftotext` / `pdfinfo` / `pdftohtml`, used to prove fonts are
  embedded and that the Japanese PDF has no mojibake.
- **Ruby + Bundler** for Jekyll, as before.

Environment notes (both handled automatically by `build_all.py`):

- Jekyll must run under a **UTF-8 locale**. With `LANG` unset Ruby defaults to
  US-ASCII and bibtex-ruby fails on the accented author names.
- Ruby is selected by chruby from the login profile, so Jekyll is invoked via
  a login shell; a bare subprocess gets `Bundler::GemNotFound`.
- The Japanese PDF uses **Hiragino Mincho ProN**, which ships with macOS. On a
  machine without it, change `FONT["cjk"]` in `scripts/lib/theme.py`.

## Layout

```
data/            authored inputs (excluded from the Jekyll build)
scripts/         pipeline; scripts/lib/ holds the modules
  Makefile       entry points  (make -C scripts help)
tests/           unittest suite
_data/cv/        GENERATED site data
_includes/       cv-section, cv-grants, featured-research, profile-bio
build/           GENERATED CVs (gitignored)
```

> **Do not run `scripts/migrate_initial_data.py --force` after the first
> migration.** It rebuilds the workbook from `scripts/migration/records.py`
> and would discard spreadsheet edits. It now refuses when the file is open in
> Excel or has been modified since; `--i-know` overrides, and should not be
> needed.

`migration_report.md` records how the initial data was merged from the old
pages, ORCID and Researchmap, which conflicts were found, and what still needs
attention.
