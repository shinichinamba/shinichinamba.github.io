# -*- coding: utf-8 -*-
"""Prose, profile fields and the migration report for the initial migration.

The English text is taken verbatim from the pre-migration index.md and the
Japanese from jp.md wherever it existed, so the site reads exactly as before.
Fields with no prior source (cv_summary, the featured-research summaries) are
drafts and are flagged as such in the migration report.
"""

SITE = "https://shinichinamba.github.io/"

PROFILE = {
    "name": {
        "ja": "難波 真一",
        "en": "Shinichi Namba",
        "reading_ja": "なんば しんいち",
    },
    "degrees": {"en": ["M.D.", "Ph.D."]},
    "contact": {
        "email": "snamba@m.u-tokyo.ac.jp",
        # Department of Genome Informatics, Graduate School of Medicine,
        # The University of Tokyo (Hongo campus).
        # Postal address only -- the department appears on the position
        # line immediately above, so repeating it here reads as a typo.
        "address": {
            "ja": "〒113-0033 東京都文京区本郷7-3-1",
            "en": "7-3-1 Hongo, Bunkyo-ku, Tokyo 113-0033, Japan",
        },
    },
    "links": {
        "website": SITE,
        "researchmap": "https://researchmap.jp/shinichinamba",
        "orcid": "https://orcid.org/0000-0002-7486-3146",
        "google_scholar": None,          # not published anywhere yet
        "github": "https://github.com/shinichinamba",
    },
    # Used by lib/cite.py to decide which author to bold.  Keep in sync with
    # how the name is written in _bibliography/*.bib.
    "self_bib_aliases": [{"family": "Namba", "given_initial": "S"}],
    "current_position": {
        "ja": "東京大学大学院医学系研究科 遺伝情報学 助教",
        "en": ("Assistant Professor, Department of Genome Informatics, "
               "Graduate School of Medicine, The University of Tokyo"),
    },
    "research_interests": {
        "ja": ("遺伝統計学 / 集団遺伝学 / がん / ゲノムワイド関連解析 / 選択圧 / "
               "ゲノム情報にもとづいた疾患予測・薬剤開発 など"),
        "en": ("Statistical Genetics / Population Genomics / Cancer / GWAS / "
               "Selection / Polygenic Score / Drug discovery ..."),
    },
    "bio_short": {
        "ja": ("東京大学大学院医学系研究科遺伝情報学（岡田随象教授）にて助教をしております。"
               "ヒトゲノムを対象とした研究を行っており、特にヒト形質の遺伝的構造の解明、"
               "疾患予測、創薬を目的としています。"
               "大阪大学大学院医学系研究科遺伝統計学（指導教官：岡田随象教授）にて"
               "博士（医学）を取得。"
               "博士課程入学以前は、東京大学大学院医学系研究科細胞情報学"
               "（現 国立がんセンター研究所細胞情報学分野）において間野博行教授・"
               "河津正人先生のご指導のもと、がんにおけるトランスクリプトーム研究および"
               "メチローム研究を行いました。"),
        "en": ("I am an assistant professor at Department of Genome Informatics, "
               "Graduate School of Medicine, The University of Tokyo, Japan "
               "(Prof. Yukinori Okada). "
               "My research focuses on human genetics. "
               "In particular, I am interested in elucidating the genetic "
               "structure of complex traits, disease risk prediction, and drug "
               "discovery. "
               "Before completing Ph.D. at Osaka University "
               "(Prof. Yukinori Okada), I studied transcriptome and methylome "
               "in cancer under Prof. Hiroyuki Mano and Dr. Masahito Kawazu at "
               "the University of Tokyo."),
    },
    # DRAFT: currently the same as bio_short.  Expand when a dedicated profile
    # page is added; nothing on the site reads this yet.
    "bio_long": {"ja": None, "en": None},
    # DRAFT: shown as "Research Profile" at the top of the CV.  Review wording.
    "cv_summary": {
        "ja": ("ヒトゲノムを対象とした遺伝統計学研究に従事している。"
               "バイオバンク規模のデータを用いて、複合形質の遺伝的構造の解明、"
               "遺伝子–環境相互作用の解析、多遺伝子リスクスコアによる疾患予測、"
               "およびゲノム情報にもとづく創薬標的の同定を主要な研究課題としている。"),
        "en": ("My research applies statistical genetics to human genome data. "
               "Using biobank-scale cohorts, I work on elucidating the genetic "
               "architecture of complex traits, characterising gene-environment "
               "interactions, evaluating polygenic risk prediction, and "
               "identifying drug targets from human genetic evidence."),
    },
}

# ``bibkey`` must resolve against _bibliography/*.bib.  Bibliographic data is
# never repeated here -- only the ordering and the plain-language summary.
# DRAFT summaries: please review the wording.
FEATURED = [
    {
        "bibkey": "Namba_2026",
        "order": 1,
        "summary_en": (
            "A cross-population survey of gene-environment interactions across "
            "biobanks. The study assembles interaction effects on a common "
            "footing so that they can be compared between populations rather "
            "than studied one cohort at a time."),
        "summary_ja": (
            "複数のバイオバンクを横断して遺伝子–環境相互作用を体系的に解析した研究。"
            "相互作用効果を共通の枠組みで整理することで、単一集団ごとの解析では"
            "困難だった集団間比較を可能にした。"),
    },
    {
        "bibkey": "Namba_2024",
        "order": 2,
        "summary_en": (
            "A comparison of polygenic score methods applied to embryo "
            "selection. Different methods rank the same embryos differently, "
            "which bears directly on how such scores should be interpreted in "
            "a reproductive setting."),
        "summary_ja": (
            "胚選択に用いられる多遺伝子スコアの手法間比較を行った研究。"
            "同一の胚に対しても手法によって順位付けが一致しないことを示し、"
            "生殖医療の文脈におけるスコア解釈の前提に検討を加えた。"),
    },
    {
        "bibkey": "cancerPRS_2022",
        "order": 3,
        "summary_en": (
            "A pan-cancer analysis linking common germline risk variants to "
            "somatic alterations and clinical features, connecting inherited "
            "risk with the tumour changes and presentation seen in patients."),
        "summary_ja": (
            "生殖細胞系列の一般的なリスク変異が、体細胞変異および臨床像と"
            "どのように関連するかを複数のがん種にわたって解析した研究。"
            "遺伝的リスクと腫瘍側の変化を結びつけた。"),
    },
    {
        "bibkey": "GBMI_DrugDiscov_2022",
        "order": 4,
        "summary_en": (
            "A practical guideline for genomics-driven drug discovery in the "
            "setting of global biobank meta-analysis, describing how "
            "large-scale multi-ancestry association results can be turned into "
            "candidate drug targets."),
        "summary_ja": (
            "国際的なバイオバンク・メタ解析を前提としたゲノム創薬の実践的指針を"
            "示した論文。大規模かつ多民族の関連解析結果を創薬標的の候補へ"
            "つなげる手順を整理した。"),
    },
]

CV_PROFILES = {
    # `en` / `ja` are the published CVs: records filtered by
    # visible_cv_short, copied to assets/cv/ and served from the site.
    #
    # `en_full` / `ja_full` are for personal reference only: every record,
    # no filtering. They are written to build/ (gitignored) and the publish
    # guard refuses to put them anywhere web-facing.
    "profiles": {
        "en": {"language": "en", "variant": "short", "publications": "both",
               "publish_to_site": True, "output": "Shinichi_Namba_CV_EN"},
        "ja": {"language": "ja", "variant": "short", "publications": "both",
               "publish_to_site": True, "output": "Shinichi_Namba_CV_JA"},
        "en_full": {"language": "en", "variant": "full", "publications": "both",
                    "publish_to_site": False,
                    "output": "Shinichi_Namba_CV_EN_full"},
        "ja_full": {"language": "ja", "variant": "full", "publications": "both",
                    "publish_to_site": False,
                    "output": "Shinichi_Namba_CV_JA_full"},
    },
    "bibliography": {
        "peer_reviewed": "_bibliography/publications.bib",
        "preprints": "_bibliography/preprints.bib",
        "reviews_ja": "_bibliography/japanese_reviews.bib",
    },
}

DATA_README = """# data/ — authored inputs

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
"""

MIGRATION_REPORT = """# Initial data migration report

Generated by `scripts/migrate_initial_data.py`.

Sources merged:

| source | what it provided |
|---|---|
| `data/legacy/index.md.snapshot`, `jp.md.snapshot` | the pre-migration website content |
| ORCID `0000-0002-7486-3146` (`pub.orcid.org/v3.0`) | employments, educations, fundings, memberships |
| Researchmap `shinichinamba` (`api.researchmap.jp`) | bilingual ja/en records for awards, grants, teaching, memberships |

Note that `researchmap.jp/shinichinamba` (the HTML page) returns HTTP 502; the
API host `api.researchmap.jp` works and returns JSON-LD with both languages,
which is what was used.

## 1. Conflicts between sources, and how each was resolved

All four were confirmed with the site owner before being written.

| fact | index.md | jp.md | ORCID | Researchmap | **adopted** |
|---|---|---|---|---|---|
| UTokyo Assistant Professor, start | Oct 2024 | 2023/10 | 2023-10-01 | 2024-10 | **2023-10** |
| RIKEN Invited Faculty, start | Nov 2024 | *(absent)* | 2023-11-01 | *(absent)* | **2023-11** |
| Osaka Invited Faculty | Oct 2024 –, ongoing | *(absent)* | 2023-10-01 → 2025-03-31 | *(absent)* | **2023-10 → 2025-03, ended** |
| Takeda scholarship, end | Mar 2024 | 2023/9 | 2024-03 | *(absent)* | **2023-09** |

The first three show a consistent pattern: the English page's Job section was
a year later than every other source. The Japanese page and ORCID agree, so
the English page was the outlier and has been corrected.

The fourth went the other way. The site owner confirmed 2023-09, which matches
the Japanese page and the end of the doctoral course; **ORCID still records
2024-03 and should be corrected there.** This is the one open item.

## 2. Records added that were not on the website

| sheet | record | source |
|---|---|---|
| awards | Travel Award, ESHG Annual Meeting 2024 (2024-10) | Researchmap |
| awards | Outstanding Doctoral Student Award, Osaka (2024-03) | Researchmap |
| grants | JSPS KAKENHI Early-Career 26K18279, 2026-04 → 2028-03, ¥4,550,000 | Researchmap, ORCID |
| teaching | Introduction to Medicine Seminar (2026-04 –) | Researchmap |
| memberships | ASHG (2020 –), JSHG (2021 –), JSBI (2021 –), JCA (2017 –) | Researchmap + ORCID join years |

Memberships were never shown on the site and are set `visible_web = FALSE`;
they appear on the CV only. The two new awards and the new grant are set
visible, so they will appear on the site after the migration.

## 3. Records with no data in any source

`invited_talks`, `reviewing`, `committees` and `patents` are empty. Researchmap
reports `presentations = 0`, `committee_memberships = 0` and
`industrial_property_rights = 0`; ORCID has no `services` or `distinctions`.
The sheets exist with headers so rows can be appended, and the corresponding
CV sections stay hidden while they are empty.

## 4. Normalisations applied

- English month names are now three-letter abbreviations throughout. The old
  page mixed `June 2024` / `July 2024` with `Oct 2024`.
- Grants are ordered by start date. The old pages ordered them differently
  from each other.
- `Apr 2020 – Mar 2024 –` (a stray trailing dash under Fellowships) is gone;
  ranges are rendered from structured dates.
- Osaka University is written **The University of Osaka** in English, matching
  its current official English name and the site owner's own Researchmap
  record. The old English page said `Osaka University`.

## 5. Bibliography repair

`_bibliography/publications.bib` contained **two different papers under the key
`Sonehara_2025`**. bibtex-ruby resolves such a collision by silently renaming
the second one (`k.succ!`), so the psoriasis whole-genome-sequencing paper was
being published under the fabricated key `Sonehara_2026`, its anchor was
unreachable, and adding a genuine `Sonehara_2026` later would have cascaded the
renaming.

The COVID-19 vaccine immunogenicity entry has been re-keyed to
`Sonehara_2025_vaccine`. Duplicate keys are now a hard validation error.

## 6. Items needing the site owner's attention

1. **ORCID fellowship end date** — ORCID says the Takeda scholarship ran to
   2024-03; the adopted value is 2023-09. Correct it in ORCID.
2. **`profile.yml: links.google_scholar` is null.** No Google Scholar profile
   URL exists in the repository or in ORCID. Fill it in if there is one.
3. **`profile.yml: cv_summary` is a draft** written for this migration. It is
   the "Research Profile" paragraph at the top of the CV — please review.
4. **`profile.yml: bio_long` is empty.** Nothing on the site reads it yet.
5. **`featured_publications.yml` summaries are drafts.** Four first/co-first
   papers were selected from the six `status = selected` entries. Review the
   wording, and add or remove entries as you see fit.
6. **`src/CV/`** still contains the abandoned R `vitae::awesomecv` CV, whose
   template placeholder text was never replaced and which cannot build here
   (no LaTeX). Consider deleting it. It also contains `src/CV/.httr-oauth`, a
   cached Google OAuth token sitting in a Dropbox-synced folder — that one is
   untracked by git but should be deleted by hand.
"""
