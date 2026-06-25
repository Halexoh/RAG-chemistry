"""Maps PDF pages to chapter identifiers, for the two book layouts we support.

Layout A — one PDF per chapter: the chapter number lives in the filename,
so no PDF parsing is needed. The 11 books loaded so far turned out to use
at least four different filename conventions for this — discovered only
once real publisher PDFs were loaded, not anticipated upfront:
  - "44044ch7.pdf"            (number directly before the extension)
  - "Ch1  introduction.pdf"   (number at the start, then a description)
  - "90725_05a.pdf"           (numeric id + underscore + chapter number,
                                optionally split into "05a"/"05b" sub-files)
  - "part 1 - paint....pdf"   ("part" instead of "ch")
Plus a separate set of non-numbered filenames for structural sections
("_fm", "_toc", "_indx", "_pref", "prefacio.pdf", "portada.pdf"...),
handled by structural_label_from_filename below. A file matching neither
is a real, untitled-by-number chapter (e.g. one article in an edited
symposium volume) — its own filename becomes the chapter title; see
extraction/run.py.

Layout B — one PDF for the whole book (e.g. a 1000+ page handbook): we read
the embedded table of contents (PyMuPDF's `get_toc()`) and turn it into a
page -> chapter_title lookup.
"""

import re
from pathlib import Path

import fitz

NUMERIC_CHAPTER_PATTERNS = [
    re.compile(r"ch(\d+)\.pdf$", re.IGNORECASE),
    re.compile(r"_0*(\d+)[a-z]?\.pdf$", re.IGNORECASE),
    re.compile(r"^ch[\s.]*0*(\d+)\b", re.IGNORECASE),
    re.compile(r"^part[\s-]*0*(\d+)\b", re.IGNORECASE),
]

# Short codes (from "<id>_<code>.pdf" style books) matched exactly against
# the stem with any leading numeric id stripped — kept exact rather than
# substring because tokens like "fm"/"ref"/"toc" are too short to safely
# match inside an unrelated real chapter title.
STRUCTURAL_STEM_LABELS = {
    "fm": "Front Matter",
    "fmpre": "Front Matter",
    "portada": "Front Matter",
    "toc": "Table of Contents",
    "contents": "Table of Contents",
    "indx": "Index",
    "index": "Index",
    "indice": "Index",
    "índice": "Index",
    "pref": "Preface",
    "pref1": "Preface",
    "pref2": "Preface",
    "preface": "Preface",
    "prefacio": "Preface",
    "fore": "Foreword",
    "foreword": "Foreword",
    "ref": "References",
    "glo": "Glossary",
    "supp": "Supplement",
}

# Longer, distinctive phrases — safe to match anywhere in the filename.
STRUCTURAL_SUBSTRING_LABELS = {
    "copyright": "Front Matter",
    "advisory board": "Front Matter",
    "author index": "Index",
    "subject index": "Index",
    "table of contents": "Table of Contents",
}


def chapter_from_filename(filename: str) -> str | None:
    """Extracts a numeric chapter from any of the filename conventions seen
    so far. Returns None if the filename has no chapter number in it."""
    for pattern in NUMERIC_CHAPTER_PATTERNS:
        match = pattern.search(filename)
        if match:
            return str(int(match.group(1)))
    return None


def structural_label_from_filename(filename: str) -> str | None:
    """Recognizes non-numbered structural sections (front matter, preface,
    index...) in English and Spanish filenames. Returns None if the
    filename doesn't look structural — callers should then treat the
    filename's own title as the chapter (see extraction/run.py)."""
    stem = Path(filename).stem.lower().strip()
    stem_no_prefix = re.sub(r"^\d+[_\s]*", "", stem).strip()

    for key, label in STRUCTURAL_STEM_LABELS.items():
        if stem_no_prefix == key or stem_no_prefix.startswith(key + " "):
            return label
    for substring, label in STRUCTURAL_SUBSTRING_LABELS.items():
        if substring in stem:
            return label
    return None


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
