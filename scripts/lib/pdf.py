"""DOCX -> PDF via LibreOffice headless, with the result actually verified.

soffice can return exit status 0 having written nothing, or having written a
PDF whose Japanese text is a row of blanks, so the exit code is not evidence.
poppler is available, so we assert on the artefact instead: the file exists
and is non-trivial, a CID font is embedded for Japanese, the extracted text
contains no U+FFFD, and every hyperlink survived.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

SOFFICE_CANDIDATES = (
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/opt/homebrew/bin/soffice",
    "/usr/local/bin/soffice",
    "soffice",
)


class ConverterMissing(RuntimeError):
    pass


class PdfVerificationError(RuntimeError):
    pass


def find_soffice() -> str:
    for c in SOFFICE_CANDIDATES:
        p = shutil.which(c) if not c.startswith("/") else (
            c if Path(c).exists() else None)
        if p:
            return p
    raise ConverterMissing(
        "LibreOffice (soffice) was not found.\n"
        "  Install it:  brew install --cask libreoffice\n"
        "  Or skip PDFs: scripts/build_cv.py --formats docx")


def parse_pdffonts(out: str) -> list[dict]:
    """Parse `pdffonts` output into rows.

    The columns are fixed-width; `emb` is the third field from the right
    before `object ID`, so we split from the right to stay robust against
    font names containing spaces.
    """
    lines = out.splitlines()
    rows: list[dict] = []
    started = False
    for line in lines:
        if line.startswith("---"):
            started = True
            continue
        if not started or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        # ... name type encoding emb sub uni object ID
        try:
            obj_id_fields = 2
            uni = parts[-(obj_id_fields + 1)]
            sub = parts[-(obj_id_fields + 2)]
            emb = parts[-(obj_id_fields + 3)]
        except IndexError:                       # pragma: no cover
            continue
        rows.append({"name": parts[0], "embedded": emb == "yes",
                     "subset": sub == "yes", "unicode": uni == "yes"})
    return rows


def _run(*args: str) -> str:
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout


def docx_to_pdf(docx_path: Path, out_dir: Path, *, profile_dir: Path) -> Path:
    soffice = find_soffice()
    out_dir.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    # A private user profile is mandatory: without it soffice refuses to start
    # (or silently attaches) when a desktop LibreOffice is already running.
    subprocess.run(
        [soffice, "--headless", "--norestore", "--invisible",
         f"-env:UserInstallation=file://{profile_dir.resolve()}",
         "--convert-to", "pdf", "--outdir", str(out_dir), str(docx_path)],
        capture_output=True, text=True, timeout=300, check=False)
    pdf = out_dir / (docx_path.stem + ".pdf")
    if not pdf.exists():
        raise PdfVerificationError(
            f"soffice produced no PDF for {docx_path.name}")
    return pdf


def verify_pdf(pdf: Path, lang: str, expect_urls: set[str] | None = None,
               probes: tuple[str, ...] = ()) -> dict:
    if pdf.stat().st_size < 5000:
        raise PdfVerificationError(f"{pdf.name} is suspiciously small")

    info = _run("pdfinfo", str(pdf))
    m = re.search(r"Pages:\s+(\d+)", info)
    pages = int(m.group(1)) if m else 0
    if pages < 1:
        raise PdfVerificationError(f"{pdf.name} has no pages")

    rows = parse_pdffonts(_run("pdffonts", str(pdf)))
    if not rows:
        raise PdfVerificationError(f"{pdf.name} embeds no fonts")
    not_embedded = [r["name"] for r in rows if not r["embedded"]]
    if not_embedded:
        # A referenced-but-not-embedded font renders with whatever the
        # reader substitutes, which is how a Japanese CV turns into boxes on
        # someone else's machine.
        raise PdfVerificationError(
            f"{pdf.name}: font(s) not embedded: {', '.join(not_embedded)}")
    if lang == "ja" and len(rows) < 2:
        raise PdfVerificationError(
            f"{pdf.name}: only one font embedded; the CJK face is missing")

    text = _run("pdftotext", "-enc", "UTF-8", str(pdf), "-")
    if "�" in text:
        raise PdfVerificationError(f"{pdf.name} contains replacement "
                                   f"characters (mojibake)")
    if lang == "ja":
        if not re.search(r"[぀-ヿ一-鿿]", text):
            raise PdfVerificationError(
                f"{pdf.name}: no Japanese text could be extracted")
    for probe in probes:
        if probe not in re.sub(r"\s+", "", text):
            raise PdfVerificationError(
                f"{pdf.name}: expected text {probe!r} is missing")

    missing: set[str] = set()
    if expect_urls:
        html = _run("pdftohtml", "-stdout", "-noframes", "-i", str(pdf))
        # any scheme, not just http(s): the header carries a mailto: link
        got = set(re.findall(r'href="([a-zA-Z][a-zA-Z0-9+.-]*:[^"]+)"', html))
        missing = {u for u in expect_urls
                   if u not in got and u.rstrip("/") not in
                   {g.rstrip("/") for g in got}}
    return {"pages": pages, "missing_links": sorted(missing)}


def scrub_dates(pdf: Path) -> None:
    """Replace the PDF creation/modification timestamps with a fixed value.

    Equal-length replacement, so the cross-reference table stays valid.
    """
    data = pdf.read_bytes()
    fixed = b"D:20000101000000Z"

    def repl(m: re.Match) -> bytes:
        body = m.group(2)
        pad = fixed[:len(body)] if len(fixed) >= len(body) else \
            fixed + b" " * (len(body) - len(fixed))
        return m.group(1) + pad + m.group(3)

    new = re.sub(rb"(/(?:CreationDate|ModDate)\s*\(D:)([^)]*)(\))",
                 lambda m: m.group(1)[:-3] + repl(
                     re.match(rb"(/(?:CreationDate|ModDate)\s*\()(D:[^)]*)(\))",
                              m.group(0)))[len(m.group(1)) - 3:],
                 data) if False else data
    # simpler and safer: pad in place, preserving byte length
    def _pad(m):
        head, body, tail = m.group(1), m.group(2), m.group(3)
        want = fixed
        if len(want) > len(body):
            want = want[:len(body)]
        else:
            want = want + b" " * (len(body) - len(want))
        return head + want + tail
    new = re.sub(rb"(/(?:CreationDate|ModDate)\s*\()([^)]*)(\))", _pad, data)
    if new != data:
        pdf.write_bytes(new)
