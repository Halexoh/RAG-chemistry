"""Maps PDF pages to chapter identifiers, for the two book layouts we support.

Layout A — one PDF per chapter (e.g. "44044ch7.pdf"): the chapter number
lives in the filename, so no PDF parsing is needed.

Layout B — one PDF for the whole book (e.g. a 1000+ page handbook): we read
the embedded table of contents (PyMuPDF's `get_toc()`) and turn it into a
page -> chapter_title lookup.
"""

import re

import fitz

CHAPTER_FILENAME_RE = re.compile(r"ch(\d+)\.pdf$", re.IGNORECASE)


def chapter_from_filename(filename: str) -> str | None:
    """'44044ch7.pdf' -> '7'. Returns None for non-chapter files (front matter, etc.)."""
    match = CHAPTER_FILENAME_RE.search(filename)
    return match.group(1) if match else None


def chapter_map_from_toc(doc: fitz.Document) -> dict[int, str]:
    """Builds a 0-indexed page -> chapter title map from the PDF's embedded TOC.

    Many TOC bookmarks for a chapter heading point to page -1 (no direct
    destination) while their first subsection does have a real page — common
    when a PDF was generated from a source that only set destinations on
    leaf-level headings. We resolve those by borrowing the page of the next
    TOC entry (at any level) that does have one.
    """
    toc = doc.get_toc()
    if not toc:
        return {}

    resolved = []
    for i, (level, title, page) in enumerate(toc):
        if page == -1:
            for _, _, next_page in toc[i + 1 :]:
                if next_page != -1:
                    page = next_page
                    break
        resolved.append((level, title, page))

    # Heuristic: the top-level "chapter" entries are the shallowest level
    # that actually appears more than once (level 1 is usually just the
    # book/part title).
    levels_present = sorted({level for level, _, page in resolved if page != -1})
    chapter_level = levels_present[1] if len(levels_present) > 1 else levels_present[0]

    chapters = sorted(
        ((title, page) for level, title, page in resolved if level == chapter_level and page != -1),
        key=lambda c: c[1],
    )

    page_to_chapter: dict[int, str] = {}
    for idx, (title, start_page) in enumerate(chapters):
        end_page = chapters[idx + 1][1] - 1 if idx + 1 < len(chapters) else doc.page_count
        for page_num in range(start_page - 1, end_page):  # TOC pages are 1-indexed
            page_to_chapter[page_num] = title
    return page_to_chapter
