"""Tests for the BibTeX layer.

The citation-parity fixtures are taken from the *rendered* site
(docs/publications/index.html), so these tests are the contract that keeps the
CV and the website showing the same thing.
"""
import sys, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from lib.bib import (Bibliography, DuplicateKeyError, Author, delatex,  # noqa: E402
                     load_bib, parse_author, parse_authors, split_authors,
                     raw_keys)
from lib.cite import cite_runs, collapse_authors, is_self, SelfName  # noqa: E402
from lib.model import plain  # noqa: E402

BIB = REPO / "_bibliography"
SELF = SelfName(family="Namba", given_initial="S")


class TestDelatex(unittest.TestCase):
    def test_accents(self):
        self.assertEqual(delatex(r'J{\"u}rgenson'), "Jürgenson")
        self.assertEqual(delatex(r"Tr{\'e}gou{\"e}t"), "Trégouët")
        self.assertEqual(delatex(r"Sin{\'{e}}ad"), "Sinéad")

    def test_broken_alignment_tab_accent(self):
        # \a' is the tabbing-environment form and is invalid here; it must not
        # leak through as a literal "a'".
        self.assertEqual(delatex(r"C{\a'a}rcel-M{\a'a}rquez"), "Cárcel-Márquez")
        self.assertEqual(delatex(r"Fern{\a'a}ndez-Cadenas"), "Fernández-Cadenas")
        self.assertEqual(delatex(r"Tr{\a'e}gou{\"e}t"), "Trégouët")

    def test_ligatures(self):
        self.assertEqual(delatex(r"B{\o}rge"), "Børge")
        self.assertEqual(delatex(r"Tybj{\ae}rg-Hansen"), "Tybjærg-Hansen")

    def test_braces_stripped_last(self):
        self.assertEqual(delatex("Elsevier {BV}"), "Elsevier BV")

    def test_passthrough_raw_utf8(self):
        self.assertEqual(delatex("Zöllner"), "Zöllner")


class TestAuthors(unittest.TestCase):
    def test_marker_family_given_order(self):
        a = parse_author("**Namba, Shinichi")
        self.assertEqual((a.family, a.given, a.initials), ("Namba", "Shinichi", "S."))
        self.assertTrue(a.corr)
        self.assertFalse(a.eq)

    def test_marker_given_family_order(self):
        a = parse_author("Shinichi *Namba")
        self.assertEqual((a.family, a.given, a.initials), ("Namba", "Shinichi", "S."))
        self.assertTrue(a.eq)
        self.assertFalse(a.corr)

    def test_marker_with_latex(self):
        a = parse_author(r'Tuuli *J{\"u}rgenson')
        self.assertEqual((a.family, a.initials), ("Jürgenson", "T."))
        self.assertTrue(a.eq)

    def test_brace_group_family(self):
        self.assertEqual(parse_author("Quentin {Le Grand}").family, "Le Grand")
        self.assertEqual(parse_author("Marion {van Vugt}").family, "van Vugt")

    def test_multiple_given_names(self):
        self.assertEqual(parse_author("Yuriko N. Koyanagi").initials, "Y. N.")

    def test_hyphenated_given(self):
        self.assertEqual(parse_author("Marie-Julie Fisch").initials, "M.-J.")

    def test_split_respects_braces(self):
        toks = split_authors("A One and Quentin {Le Grand and Sons} and B Two")
        self.assertEqual(len(toks), 3)

    def test_dedup_keeps_first_and_merges_markers(self):
        a = parse_authors("Namba, Shinichi and Foo, Bar and **Namba, Shinichi")
        self.assertEqual(len(a), 2)
        self.assertTrue(a[0].corr)   # marker merged onto the first occurrence


class TestLoading(unittest.TestCase):
    def test_no_duplicate_keys(self):
        bib = Bibliography.load(BIB)
        self.assertEqual(len(bib.all), 48)
        self.assertEqual(len(bib.by_key), 48)

    def test_counts_per_file(self):
        bib = Bibliography.load(BIB)
        self.assertEqual(len(bib.groups["publications"]), 40)
        self.assertEqual(len(bib.groups["preprints"]), 6)
        self.assertEqual(len(bib.groups["reviews_ja"]), 2)

    def test_bare_unbraced_status_value(self):
        bib = Bibliography.load(BIB)
        sel = bib.selected()
        self.assertEqual(len(sel), 6)
        self.assertIn("Namba_2026", {e.key for e in sel})

    def test_duplicate_key_raises(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".bib", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("@article{A, title={x}, author={A B}, year={2020}}\n"
                     "@article{A, title={y}, author={C D}, year={2021}}\n")
            p = Path(fh.name)
        with self.assertRaises(DuplicateKeyError):
            load_bib(p, "t")
        p.unlink()

    def test_raw_keys_sees_leading_space_entries(self):
        text = (BIB / "publications.bib").read_text(encoding="utf-8")
        self.assertEqual(len(raw_keys(text)), 40)

    def test_self_matches_most_entries(self):
        bib = Bibliography.load(BIB)
        hits = sum(1 for e in bib.groups["publications"]
                   if any(is_self(a, SELF) for a in e.authors))
        self.assertGreaterEqual(hits, 35)   # canary for a parser regression


class TestCitationParity(unittest.TestCase):
    """Expected strings lifted from the rendered docs/publications/index.html."""

    def setUp(self):
        self.bib = Bibliography.load(BIB)

    def cite(self, key):
        return plain(cite_runs(self.bib.by_key[key], SELF))

    def test_et_al_with_self_truncated_away(self):
        self.assertEqual(
            self.cite("Sato_2026"),
            "Sato, G., Yamamoto, Y., Sonehara, K., Saiki, R., Ojima, T., ..., "
            "Namba, S. et al. Genetic regulation across germline and somatic "
            "variation on the Y chromosome contributes to type 2 diabetes. "
            "Nature Medicine 894–905 (2026).")

    def test_self_first_no_gap(self):
        self.assertEqual(
            self.cite("Namba_2026"),
            "**Namba, S., Sonehara, K., Koyanagi, Y. N., Kikuchi, T., "
            "Ojima, T., Edahiro, R. et al. A cross-population compendium of "
            "gene–environment interactions. Nature 688–697 (2026).")

    def test_volume_present(self):
        self.assertEqual(
            self.cite("cancerPRS_2022"),
            "*Namba, S., *Saito, Y., Kogure, Y., Masuda, T., Bondy, M. L., "
            "Gharahkhani, P. et al. Common germline risk variants impact "
            "somatic alterations and clinical features across cancers. "
            "Cancer Research 83, 20–27 (2022).")

    def test_two_authors_use_ampersand(self):
        self.assertEqual(
            self.cite("Namba2024"),
            "Namba, S. & Okada, Y. [CURRENT PIPELINES FOR WHOLE-GENOME "
            "SEQUENCING ANALYSES]. Arerugi 72, 1110–1112 (2023).")

    def test_preprint_without_volume_or_pages(self):
        self.assertEqual(
            self.cite("Palmer_2026"),
            "Palmer, D. S., Hill, B., Hodgson, S., Jõeloo, M., Kalantzis, G., "
            "..., Namba, S. et al. The Biobank Rare Variant consortium powers "
            "the discovery of rare genetic associations through global "
            "collaboration. medRxiv (2026).")

    def test_markers_preserved_for_coauthors(self):
        self.assertTrue(self.cite("mishra2022stroke").startswith(
            "*Mishra, A., *Malik, R., *Hachiya, T., *Jürgenson, T., "
            "*Namba, S., *Posner, D. C. et al."))

    def test_html_entities_unescaped_in_fields(self):
        self.assertIn("Alimentary Pharmacology & Therapeutics",
                      self.cite("De_Vincentis_2024"))
        self.assertNotIn("&amp;", self.cite("De_Vincentis_2024"))

    def test_page_dash_normalized_to_en_dash(self):
        self.assertIn("1110–1112", self.cite("Namba2024"))

    def test_self_name_always_bold(self):
        for e in self.bib.groups["publications"]:
            runs = cite_runs(e, SELF)
            bold = [r for r in runs if r.bold and "Namba, S" in r.text]
            self.assertTrue(bold, f"{e.key}: self name not bold")

    def test_title_carries_doi_link(self):
        runs = cite_runs(self.bib.by_key["Namba_2026"], SELF)
        hrefs = {r.href for r in runs if r.href}
        self.assertIn("https://doi.org/10.1038/s41586-025-10054-6", hrefs)

    def test_html_italics_in_title_become_runs(self):
        runs = cite_runs(self.bib.by_key["Kyosaka_2026"], SELF)
        ital = [r.text for r in runs if r.italic]
        self.assertIn("Helicobacter pylori", ital)
        self.assertNotIn("<i>", plain(runs))


class TestWholeCorpusParity(unittest.TestCase):
    """Every citation must match what the built site renders, verbatim.

    This is the contract that stops the CV and the website drifting apart.
    If docs/ is rebuilt the fixtures update themselves, so the test stays
    honest without a golden file to maintain by hand.
    """

    def test_all_entries_match_rendered_site(self):
        import html as _html
        import re as _re
        page = REPO / "docs" / "publications" / "index.html"
        if not page.exists():                      # pragma: no cover
            self.skipTest("docs/ not built")
        site = page.read_text(encoding="utf-8")

        def rendered(key):
            """The COLLAPSED author view, as a reader first sees it.

            The author list is now wrapped in <span class="authors"> with the
            middle authors in hidden spans, so the citation text has to be
            reconstructed: drop anything hidden, drop the toggle links, keep
            the ", ..., " gap and the "et al.".
            """
            m = _re.search(r'id="%s">(.*?)<br' % _re.escape(key), site, _re.S)
            if not m:
                return None
            frag = m.group(1)
            frag = _re.sub(r"<span[^>]*\bhidden\b[^>]*>.*?</span>", "", frag,
                           flags=_re.S)
            frag = _re.sub(r"<a[^>]*\bau-toggle\b[^>]*>.*?</a>", "", frag,
                           flags=_re.S)
            txt = _html.unescape(_re.sub(r"<[^>]+>", "", frag))
            return _re.sub(r"\s+", " ", txt).strip()

        bib = Bibliography.load(BIB)
        checked = 0
        for e in bib.all:
            exp = rendered(e.key)
            if exp is None and e.key == "Sonehara_2025_vaccine":
                # docs/ predates the duplicate-key fix
                exp = rendered("Sonehara_2026")
            if exp is None:
                continue
            from lib.bib import normalize_glyphs
            self.assertEqual(normalize_glyphs(plain(cite_runs(e, SELF))).rstrip(),
                             normalize_glyphs(exp).rstrip(),
                             f"citation drift for {e.key}")
            checked += 1
        self.assertGreaterEqual(checked, 48)


class TestCollapse(unittest.TestCase):
    def mk(self, n, self_at=None):
        out = []
        for i in range(n):
            if self_at is not None and i == self_at:
                out.append(Author("Namba", "Shinichi", "S."))
            else:
                out.append(Author(f"F{i}", f"G{i}", "G."))
        return out

    def test_short_list_untouched(self):
        shown, trunc, gap = collapse_authors(self.mk(6), SELF)
        self.assertEqual(len(shown), 6)
        self.assertFalse(trunc)

    def test_seven_authors_shown_in_full(self):
        # The site does not truncate a 7-author list; see collapse_authors().
        shown, trunc, gap = collapse_authors(self.mk(7), SELF)
        self.assertEqual(len(shown), 7)
        self.assertFalse(trunc)

    def test_eight_authors_collapse_to_six(self):
        shown, trunc, gap = collapse_authors(self.mk(8), SELF)
        self.assertEqual(len(shown), 6)
        self.assertTrue(trunc)

    def test_self_inside_first_six(self):
        shown, trunc, gap = collapse_authors(self.mk(20, self_at=2), SELF)
        self.assertEqual(len(shown), 6)
        self.assertTrue(trunc)
        self.assertIsNone(gap)

    def test_self_outside_first_six(self):
        shown, trunc, gap = collapse_authors(self.mk(20, self_at=11), SELF)
        self.assertEqual(len(shown), 6)
        self.assertTrue(trunc)
        self.assertEqual(gap, 5)
        self.assertEqual(shown[5].family, "Namba")


if __name__ == "__main__":
    unittest.main(verbosity=2)
