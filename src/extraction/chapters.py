"""Maps PDF pages to chapter identifiers, for the two book layouts we support.

Layout A — one PDF per chapter: the chapter number lives in the filename,
so no PDF parsing is needed. Filename conventions kept growing every time a
new source of books was loaded — never anticipated upfront, always
discovered from real files:
  - "44044ch7.pdf"            (number directly before the extension)
  - "Ch1  introduction.pdf"   (number at the start, then a description)
  - "90725_05a.pdf"           (numeric id + underscore + chapter number,
                                optionally split into "05a"/"05b" sub-files)
  - "part 1 - paint....pdf"   ("part" instead of "ch")
  - "Cap_01_Introduccion.pdf" (Spanish "Cap_"/"Sec_" + number, then a
                                description — own personal archive's
                                convention, also splits into "05a"/"05b")
Plus a separate set of non-numbered filenames for structural sections
("_fm", "_toc", "_indx", "_pref", "prefacio.pdf", "portada.pdf",
"00_Tabla_de_Contenido.pdf", "ZZ_Indice.pdf"...), handled by
structural_label_from_filename below. A file matching neither is a real,
untitled-by-number chapter (e.g. one article in an edited symposium
volume) — its own filename becomes the chapter title; see extraction/run.py.

Some chapters showed up twice: an original file plus a "_v2"-suffixed one
with identical content (re-scanned/re-exported later, original never
deleted) — not a sub-part like "05a"/"05b", a full duplicate. See
version_suffix() / dedupe_versioned_chapters() below: the rule that tells
the two apart is the explicit "_vN" marker, not just sharing a chapter
number.

Layout B — one PDF for the whole book (e.g. a 1000+ page handbook): we read
the embedded table of contents (PyMuPDF's `get_toc()`) and turn it into a
page -> chapter_title lookup.
"""

import hashlib
import re
from pathlib import Path

import fitz

NUMERIC_CHAPTER_PATTERNS = [
    re.compile(r"ch(\d+)\.pdf$", re.IGNORECASE),
    re.compile(r"_0*(\d+)[a-z]?\.pdf$", re.IGNORECASE),
    re.compile(r"^ch[\s.]*0*(\d+)\b", re.IGNORECASE),
    re.compile(r"^part[\s-]*0*(\d+)\b", re.IGNORECASE),
    re.compile(r"^cap[_\s]*0*(\d+)[a-z]?", re.IGNORECASE),
    re.compile(r"^sec[_\s]*0*(\d+)[a-z]?", re.IGNORECASE),
]

VERSION_SUFFIX_PATTERN = re.compile(r"_v(\d+)\.pdf$", re.IGNORECASE)

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
    "contenido": "Table of Contents",
    "tabla de contenido": "Table of Contents",
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
    "referencias": "References",
    "glo": "Glossary",
    "glosario": "Glossary",
    "supp": "Supplement",
    "directorio": "Supplement",
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
    filename's own title as the chapter (see extraction/run.py).

    Underscores/hyphens are normalized to spaces before matching — some
    sources title-case with spaces ("prefacio 1a edición.pdf"), others use
    underscores throughout ("00_Prefacio_1a_Edicion.pdf"); matching should
    not depend on which style a given source happens to use.
    """
    stem = Path(filename).stem.lower().strip()
    normalized = re.sub(r"[_-]+", " ", stem).strip()
    # Leading numeric id ("00 ", "13372 ") or the "zz" sentinel some sources
    # use for trailing sections (e.g. "ZZ_Indice.pdf" -> an index at the end).
    normalized_no_prefix = re.sub(r"^(?:\d+|zz)\s*", "", normalized).strip()

    for key, label in STRUCTURAL_STEM_LABELS.items():
        if normalized_no_prefix == key or normalized_no_prefix.startswith(key + " "):
            return label
    for substring, label in STRUCTURAL_SUBSTRING_LABELS.items():
        if substring in normalized:
            return label
    return None


def version_suffix(filename: str) -> int:
    """Returns the explicit version number from a "..._vN.pdf" filename, or
    1 if there's no such marker — the implicit, original version."""
    match = VERSION_SUFFIX_PATTERN.search(filename)
    return int(match.group(1)) if match else 1


def dedupe_versioned_chapters(filenames_by_chapter: dict[str, list[str]]) -> dict[str, list[str]]:
    """Within each chapter's file list, drops superseded versions.

    Two different things look identical at the "same chapter number" level:
    a chapter genuinely split into sub-parts ("Cap_05a_..._Parte1.pdf",
    "Cap_05b_..._Parte2.pdf" — different content, both real, both kept),
    and a chapter re-exported later with an explicit "_v2" marker over the
    original file left in place by mistake (identical content, only the
    highest version should survive). The deciding signal is the explicit
    "_vN" suffix: if at least one filename in a chapter's group has one,
    every file in that group is a revision of the same content and only
    the highest version is kept; if none do, every file is a genuine
    distinct sub-part and all are kept.
    """
    result = {}
    for chapter, names in filenames_by_chapter.items():
        if any(VERSION_SUFFIX_PATTERN.search(name) for name in names):
            max_version = max(version_suffix(name) for name in names)
            result[chapter] = [name for name in names if version_suffix(name) == max_version]
        else:
            result[chapter] = list(names)
    return result


def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def drop_exact_duplicate_files(paths: list[Path]) -> list[Path]:
    """Drops byte-identical files, keeping the first occurrence (by sorted
    filename) of each distinct content.

    Found in a real archive: "Sec_11_Miscelaneos.pdf" and
    "Sec_11b_Miscelaneos_cont.pdf" inside the same book — the "_cont"
    suffix implies a continuation with different content, but they turned
    out to be an exact copy-paste accident. dedupe_versioned_chapters()
    only catches duplicates with an explicit "_vN" marker; this catches
    the rest, by content rather than by filename convention, so it needs
    no naming signal at all.
    """
    seen_hashes: set[str] = set()
    kept = []
    for path in sorted(paths, key=lambda p: p.name):
        digest = file_hash(path)
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        kept.append(path)
    return kept


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
    if not levels_present:
        # A TOC can exist but be pure navigation links (e.g. a short article
        # PDF whose bookmarks are "NACE Home Page", "Search Site"...) with
        # every entry at page -1 and no sibling anywhere to borrow a real
        # page from. Nothing here is usable as a chapter map.
        return {}
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
