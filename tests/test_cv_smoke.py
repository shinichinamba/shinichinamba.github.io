"""End-to-end checks on the generated CVs.

Structural assertions rather than golden files: a golden CV with 48
publications would be unmaintainable, and these catch the failures that
actually matter (drift between renderers, a leak of full-CV data to the web,
Japanese text that renders as boxes).
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from lib.bib import Bibliography  # noqa: E402
from lib.model import plain  # noqa: E402
from lib.cite import CV_STYLE, SITE_STYLE  # noqa: E402
from lib.pdf import parse_pdffonts, _run  # noqa: E402
from lib.profile import load_cv_profiles, load_profile  # noqa: E402
from lib.records import load_master  # noqa: E402
from lib.report import Report  # noqa: E402
from lib.sections import build_document, load_config  # noqa: E402

BUILD = REPO / "build" / "cv"
ASSETS = REPO / "assets" / "cv"
PUBLIC = {"Shinichi_Namba_CV_EN.pdf", "Shinichi_Namba_CV_JA.pdf"}
EN_PDF = BUILD / "Shinichi_Namba_CV_EN.pdf"
JA_PDF = BUILD / "Shinichi_Namba_CV_JA.pdf"


def _ctx():
    rep = Report()
    master = load_master(REPO / "data" / "cv_master.xlsx", rep)
    profile = load_profile(REPO / "data" / "profile.yml", rep)
    profiles = load_cv_profiles(REPO / "data" / "cv_profiles.yml", rep)
    bib = Bibliography.load(REPO / "_bibliography")
    return master, profile, profiles, bib, load_config()


def _ids(doc):
    return {plain(list(e.body)) for s in doc.sections for e in s.entries}


class TestDocumentModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master, cls.profile, cls.profiles, cls.bib, cls.cfg = _ctx()

    def doc(self, name):
        return build_document(self.master, self.profile, self.bib,
                              self.profiles[name], self.cfg)

    def test_published_and_private_profiles(self):
        self.assertEqual(set(self.profiles), {"en", "ja", "en_full", "ja_full"})
        for n in ("en", "ja"):
            self.assertTrue(self.profiles[n].publish_to_site)
            self.assertEqual(self.profiles[n].visibility_column,
                             "visible_cv_short")
        for n in ("en_full", "ja_full"):
            self.assertFalse(self.profiles[n].publish_to_site)
            self.assertIsNone(self.profiles[n].visibility_column,
                              "the private copy must be unfiltered")

    def test_private_copy_is_a_superset(self):
        """Everything hidden from the published CV survives in build/."""
        pub = {plain(list(e.body)) for s in self.doc("en").sections
               for e in s.entries}
        full = {plain(list(e.body)) for s in self.doc("en_full").sections
                for e in s.entries}
        self.assertTrue(pub <= full, pub - full)
        pg = next(s for s in self.doc("en").sections if s.key == "grants")
        fg = next(s for s in self.doc("en_full").sections if s.key == "grants")
        self.assertLess(len(pg.entries), len(fg.entries))
        self.assertEqual(len(fg.entries), len(self.master["grants"].records))

    def test_section_order(self):
        """Career record, selected publications, narrative, profiles, list."""
        for name in self.profiles:
            keys = [s.key for s in self.doc(name).sections]
            self.assertEqual(
                keys[-5:],
                ["publications", "research_interests", "personal_statements",
                 "public_profiles", "publications_full"],
                f"{name}: unexpected tail")
            self.assertLess(keys.index("teaching"), keys.index("publications"))

    def test_no_repeated_sections(self):
        for name in self.profiles:
            keys = [s.key for s in self.doc(name).sections]
            self.assertEqual(len(keys), len(set(keys)), f"{name}: duplicates")

    def test_selected_and_full_counts(self):
        doc = self.doc("en")
        sel = next(s for s in doc.sections if s.key == "publications")
        full = next(s for s in doc.sections if s.key == "publications_full")
        self.assertEqual(len(sel.entries), len(self.bib.selected()))
        self.assertEqual([len(x.entries) for x in full.subsections],
                         [6, 40, 2], "preprints must come first")

    def test_memberships_are_not_on_the_cv(self):
        for name in ("en", "ja"):
            self.assertNotIn("memberships",
                             {s.key for s in self.doc(name).sections})

    def test_markers_follow_the_name(self):
        doc = self.doc("en")
        sel = next(s for s in doc.sections if s.key == "publications")
        text = " ".join(plain(list(e.body)) for e in sel.entries)
        self.assertIn("Namba S\u266f", text)      # Namba S♯
        self.assertIn("Namba S*", text)
        self.assertNotIn("\u266fNamba", text)
        self.assertNotIn("*Namba", text)

    def test_research_interests_has_no_trailing_filler(self):
        for name, filler in (("ja", "など"), ("en", "...")):
            sec = next(s for s in self.doc(name).sections
                       if s.key == "research_interests")
            self.assertFalse(plain(list(sec.entries[0].body)).endswith(filler))

    def test_advisor_line_is_body_sized(self):
        doc = self.doc("en")
        edu = next(s for s in doc.sections if s.key == "education")
        detail = [r for e in edu.entries for r in e.detail]
        self.assertTrue(detail, "expected an advisor line")
        self.assertFalse(any(r.small for r in detail),
                         "the advisor line must not be shrunk")

    def test_section_headings(self):
        en = {s.key: s.heading for s in self.doc("en").sections}
        ja = {s.key: s.heading for s in self.doc("ja").sections}
        self.assertEqual(en["personal_statements"], "Personal Statements")
        self.assertEqual(ja["grants"], "競争的資金")
        self.assertEqual(ja["fellowships"], "奨学助成")

    def test_amounts_and_grant_numbers_stay_off_the_cv(self):
        """They are switched off in cv_master.xlsx; the CV is published."""
        for name in ("en", "ja"):
            text = " ".join(_ids(self.doc(name)))
            self.assertNotIn("4,550,000", text)
            self.assertNotIn("26K18279", text)
            self.assertNotIn("Grant No", text)

    def test_photo_only_on_the_japanese_cv(self):
        self.assertIsNone(self.doc("en").meta["photo"])
        self.assertTrue(self.doc("ja").meta["photo"])
        self.assertTrue((REPO / self.doc("ja").meta["photo"]).exists())

    def test_header_has_address_and_no_online_links(self):
        for name in ("en", "ja"):
            header = next(s for s in self.doc(name).sections
                          if s.key == "header")
            text = " ".join(plain(list(e.body)) for e in header.entries)
            self.assertIn("113-0033", text)
            hrefs = {r.href for e in header.entries for r in e.body if r.href}
            self.assertTrue(all(h.startswith("mailto:") for h in hrefs), hrefs)

    def test_public_profiles_plain_text_for_orcid_and_researchmap(self):
        for name in ("en", "ja"):
            sec = next(s for s in self.doc(name).sections
                       if s.key == "public_profiles")
            for e in sec.entries:
                text = plain(list(e.body))
                linked = any(r.href for r in e.body)
                if "orcid" in text.lower() or "researchmap" in text.lower():
                    self.assertFalse(linked, f"{text} must not be a hyperlink")
                    self.assertIn("https://", text)

    def test_cv_uses_compact_author_names_and_the_new_marker(self):
        doc = self.doc("en")
        sel = next(s for s in doc.sections if s.key == "publications")
        text = " ".join(plain(list(e.body)) for e in sel.entries)
        self.assertIn("Namba S", text)
        self.assertNotIn("Namba, S.", text)
        self.assertIn(CV_STYLE.corr_marker, text)
        self.assertNotIn("**Namba", text)

    def test_website_citation_style_is_unchanged(self):
        """The site keeps `Namba, S.` and `**`; only the CV changed."""
        self.assertEqual(SITE_STYLE.corr_marker, "**")
        self.assertTrue(SITE_STYLE.name_comma)
        self.assertTrue(SITE_STYLE.initial_periods)

    def test_self_name_bold_in_every_publication(self):
        doc = self.doc("en")
        full = next(s for s in doc.sections if s.key == "publications_full")
        for sub in full.subsections:
            for e in sub.entries:
                self.assertTrue(
                    any(r.bold and "Namba S" in r.text for r in e.body),
                    f"self name not bold: {plain(list(e.body))[:60]}")

    def test_gated_amount_stays_off_the_published_cv(self):
        text = " ".join(_ids(self.doc("en")))
        self.assertNotIn("4,550,000", text)

    def test_ja_merges_clinical_training(self):
        ja = self.doc("ja")
        self.assertNotIn("clinical_training", {s.key for s in ja.sections})
        appts = next(s for s in ja.sections if s.key == "appointments")
        self.assertIn("日本赤十字社医療センター",
                      " ".join(plain(list(e.body)) for e in appts.entries))

    def test_empty_sheets_produce_no_section(self):
        for name in self.profiles:
            self.assertNotIn("invited_talks",
                             {s.key for s in self.doc(name).sections})


@unittest.skipUnless(EN_PDF.exists(), "run `make -C scripts cv` first")
class TestArtifacts(unittest.TestCase):
    def test_only_two_public_pdfs(self):
        self.assertEqual({p.name for p in ASSETS.glob("*")}, PUBLIC)

    def test_private_full_cvs_stay_in_build(self):
        for name in ("Shinichi_Namba_CV_EN_full", "Shinichi_Namba_CV_JA_full"):
            self.assertTrue((BUILD / f"{name}.pdf").exists(), name)
            self.assertFalse((ASSETS / f"{name}.pdf").exists(),
                             f"{name} must never be published")

    def test_no_docx_is_published(self):
        self.assertEqual(list(ASSETS.glob("*.docx")), [])

    def test_all_fonts_embedded(self):
        for pdf in BUILD.glob("*.pdf"):
            rows = parse_pdffonts(_run("pdffonts", str(pdf)))
            self.assertTrue(rows, f"{pdf.name}: no fonts")
            for r in rows:
                self.assertTrue(r["embedded"],
                                f"{pdf.name}: {r['name']} not embedded")

    def test_japanese_pdf_has_no_mojibake(self):
        text = _run("pdftotext", "-enc", "UTF-8", str(JA_PDF), "-")
        self.assertNotIn("�", text)
        for probe in ("職歴", "学歴", "受賞歴", "競争的資金", "奨学助成"):
            self.assertIn(probe, text, f"{probe} missing")

    def test_footer_on_every_page(self):
        import re
        for pdf in (EN_PDF, JA_PDF):
            info = _run("pdfinfo", str(pdf))
            pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
            text = _run("pdftotext", "-enc", "UTF-8", str(pdf), "-")
            self.assertEqual(text.count("S Namba | Curriculum Vitae"), pages,
                             f"{pdf.name}: footer missing on some pages")

    def test_page_numbers_are_right_aligned(self):
        out = _run("pdftotext", "-enc", "UTF-8", "-layout", "-f", "1", "-l", "1",
                   str(EN_PDF), "-")
        line = [l for l in out.splitlines()
                if "S Namba | Curriculum Vitae" in l][0]
        self.assertTrue(line.rstrip().endswith("1"), repr(line))
        self.assertGreater(line.index("1", 30), 80, "page number not at right")

    def test_orcid_and_researchmap_are_not_hyperlinks(self):
        html = _run("pdftohtml", "-stdout", "-noframes", "-i", str(EN_PDF))
        self.assertNotIn('href="https://orcid', html)
        self.assertNotIn('href="https://researchmap', html)
        self.assertIn('href="https://shinichinamba.github.io/"', html)

    def test_docx_build_is_deterministic(self):
        """Build twice and compare, rather than trusting whatever is on disk.

        Comparing against an existing artefact makes this test fail whenever
        the data changed since the last build, which says nothing about
        determinism.
        """
        import hashlib
        hashes = []
        with tempfile.TemporaryDirectory() as tmp:
            for _ in range(2):
                r = subprocess.run(
                    [sys.executable, "scripts/build_cv.py", "--profile", "en",
                     "--formats", "docx", "--out", tmp, "-q"],
                    cwd=REPO, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                out = Path(tmp) / "Shinichi_Namba_CV_EN.docx"
                hashes.append(hashlib.sha256(out.read_bytes()).hexdigest())
        self.assertEqual(hashes[0], hashes[1], "DOCX bytes differ between "
                                               "two identical builds")

    def test_page_budget(self):
        import re
        for pdf in (EN_PDF, JA_PDF):
            info = _run("pdfinfo", str(pdf))
            pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
            self.assertLessEqual(pages, 12, f"{pdf.name} grew to {pages} pages")


class TestPublishGuard(unittest.TestCase):
    def run_cv(self, *args):
        return subprocess.run([sys.executable, "scripts/build_cv.py", *args],
                              cwd=REPO, capture_output=True, text=True)

    def test_writing_into_assets_is_refused(self):
        r = self.run_cv("--profile", "en", "--out", "assets/cv", "--publish")
        self.assertEqual(r.returncode, 5, r.stdout + r.stderr)
        self.assertEqual({p.name for p in ASSETS.glob("*")}, PUBLIC)

    def test_unknown_profile_is_a_usage_error(self):
        self.assertEqual(self.run_cv("--profile", "nope").returncode, 2)

    def test_bad_format_is_a_usage_error(self):
        self.assertEqual(self.run_cv("--formats", "xyz").returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
