"""Prints the paper to PDF and sets its author field.

    uv run --no-project --with pypdf python scripts/paper_pdf.py

`paper/paper.html` is printed to `paper/paper.pdf` with headless Chrome (A4, no
header or footer, a fresh profile each run, removed after), and the PDF's Author
field is then set to the author line the paper carries, as the author's other
PDFs have it (Plone, 2026-10-27). Chrome writes the Title from `<title>`, and no
Author: a print alone leaves the field empty. pypdf is the one dependency, and
only here.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

AUTHOR = "Huỳnh Mai Phúc (Plone Mraz)"

PAPER = Path(__file__).resolve().parent.parent / "paper"


def main() -> None:
    html, pdf = PAPER / "paper.html", PAPER / "paper.pdf"
    profile = Path(tempfile.mkdtemp(prefix="paper-chrome-"))
    try:
        subprocess.run(
            ["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
             f"--user-data-dir={profile}", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf}", html.as_uri()],
            check=True, capture_output=True)
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    writer = PdfWriter(clone_from=PdfReader(pdf))
    writer.add_metadata({"/Author": AUTHOR})
    with pdf.open("wb") as f:
        writer.write(f)
    meta = PdfReader(pdf).metadata
    print(f"{pdf}: {len(PdfReader(pdf).pages)} pages, "
          f"Title {meta.title!r}, Author {meta.author!r}")


if __name__ == "__main__":
    main()
