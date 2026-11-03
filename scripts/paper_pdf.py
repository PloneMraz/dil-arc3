"""Prints the paper to PDF in the house style of the author's PDFs, and sets its
metadata.

    uv run --no-project --with pypdf python scripts/paper_pdf.py

`paper/paper.html` is printed to `paper/paper.pdf` with headless Chrome, in the
layout of SP.pdf that the workspace's `scripts/pdf-style.md` measures (Letter,
1 in margins, Cambria; Plone, 2026-11-03): the page's own CSS holds the
measurements, and this script adds what a page alone cannot — the table of
contents on a page of its own after the Abstract, two levels, with the page each
heading falls on. Those page numbers are found by printing with a marker in every
heading, reading where each marker falls (poppler's `pdftotext`), and printing
again until they settle; the last print has no markers.

Cambria is read from the workspace's `Plone's documents/Fonts` (`PAPER_FONTS`
names another folder) through a fontconfig file of the run's own; it is licensed
with Windows and Office and is not in this repository. Without it Chrome falls
back to DejaVu Serif and the pages come out otherwise: the script says so.

The PDF's Title is the paper's full title and its Author the author line the
paper carries, as the author's other PDFs have them (Plone, 2026-10-27). pypdf is
the one dependency, and only here.
"""

from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

AUTHOR = "Huỳnh Mai Phúc (Plone Mraz)"
TITLE = "Expect, Collide, Revise: Learning From Mismatch, Every Step on the Record"

REPO = Path(__file__).resolve().parent.parent
PAPER = REPO / "paper"
FONTS = Path(os.environ.get("PAPER_FONTS", REPO.parent / "Plone's documents" / "Fonts"))
TOC_AT = "<!-- toc: scripts/paper_pdf.py puts the table of contents here -->"
HEADING = re.compile(r'<(h[23])( class="[^"]*")?>(.*?)</\1>', re.S)


def headings(page: str) -> list[tuple[int, str, str]]:
    """(level, id, text) for every section heading, in order: h2 is level 1,
    h3 level 2. The title block's h1 is not one."""
    out, seen = [], set()
    for m in HEADING.finditer(page):
        text = re.sub(r"<[^>]+>", "", m.group(3)).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", html.unescape(text).lower()).strip("-") or "h"
        while slug in seen:
            slug += "-"
        seen.add(slug)
        out.append((1 if m.group(1) == "h2" else 2, slug, m.group(3).strip()))
    return out


def render(page: str, heads: list, pages: list[int] | None, markers: bool) -> str:
    """The page with ids on its headings, the contents page in place, and, for
    the printing that finds page numbers, a marker in each heading."""
    k = iter(range(len(heads)))

    def tag(m: re.Match) -> str:
        i = next(k)
        mark = f'<span class="marker">@@H{i}@@</span>' if markers else ""
        return f'<{m.group(1)} id="{heads[i][1]}"{m.group(2) or ""}>{m.group(3)}{mark}</{m.group(1)}>'

    page = HEADING.sub(tag, page)
    rows = "".join(
        f'<li class="l{lvl}"><a href="#{hid}"><span class="t">{text}</span>'
        f'<span class="dots"></span><span class="pg">{pages[i] if pages else "00"}</span></a></li>'
        for i, (lvl, hid, text) in enumerate(heads))
    nav = f'<nav class="toc-page"><h2>Table of Contents</h2><ol class="toc">{rows}</ol></nav>'
    if TOC_AT not in page:
        raise SystemExit(f"paper.html has no line {TOC_AT!r}")
    return page.replace(TOC_AT, nav)


def chrome_pdf(html_path: Path, pdf: Path, env: dict) -> None:
    profile = Path(tempfile.mkdtemp(prefix="paper-chrome-"))
    try:
        subprocess.run(
            ["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox",
             f"--user-data-dir={profile}", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf}", html_path.as_uri()],
            check=True, capture_output=True, env=env)
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def marker_pages(pdf: Path, n: int) -> list[int]:
    text = subprocess.run(["pdftotext", str(pdf), "-"], check=True,
                          capture_output=True).stdout.decode()
    found: dict[int, int] = {}
    for page_no, page in enumerate(text.split("\f"), start=1):
        for m in re.finditer(r"@@H(\d+)@@", page):
            found.setdefault(int(m.group(1)), page_no)
    missing = [i for i in range(n) if i not in found]
    if missing:
        raise SystemExit(f"headings not found in the PDF: {missing}")
    return [found[i] for i in range(n)]


def main() -> None:
    source, pdf = PAPER / "paper.html", PAPER / "paper.pdf"
    page = source.read_text()
    heads = headings(page)
    # The printed page sits beside paper.html, so that its figures resolve.
    printed = PAPER / ".paper-print.html"
    work = Path(tempfile.mkdtemp(prefix="paper-fonts-"))
    env = dict(os.environ)
    if all((FONTS / f).exists() for f in ("cambria.ttc", "cambriab.ttf", "cambriai.ttf", "cambriaz.ttf")):
        conf = work / "fonts.conf"
        conf.write_text(
            '<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>'
            f"<dir>{html.escape(str(FONTS))}</dir><cachedir>{html.escape(str(work / 'fc-cache'))}</cachedir>"
            '<include ignore_missing="yes">/etc/fonts/fonts.conf</include></fontconfig>\n')
        env["FONTCONFIG_FILE"] = str(conf)
    else:
        print(f"warning: no Cambria in {FONTS}; the PDF falls back to DejaVu Serif")
    try:
        pages = None
        for _ in range(4):
            printed.write_text(render(page, heads, pages, markers=True))
            chrome_pdf(printed, pdf, env)
            found = marker_pages(pdf, len(heads))
            if found == pages:
                break
            pages = found
        else:
            raise SystemExit("page numbers did not settle")
        printed.write_text(render(page, heads, pages, markers=False))
        chrome_pdf(printed, pdf, env)
    finally:
        printed.unlink(missing_ok=True)
        shutil.rmtree(work, ignore_errors=True)
    writer = PdfWriter(clone_from=PdfReader(pdf))
    writer.add_metadata({"/Title": TITLE, "/Author": AUTHOR})
    with pdf.open("wb") as f:
        writer.write(f)
    meta = PdfReader(pdf).metadata
    print(f"{pdf}: {len(PdfReader(pdf).pages)} pages, "
          f"Title {meta.title!r}, Author {meta.author!r}")


if __name__ == "__main__":
    main()
