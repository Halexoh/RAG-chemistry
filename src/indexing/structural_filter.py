"""Excludes structural (non-content) sections from the search index.

Found while evaluating phase 7: out-of-domain questions correctly
triggered a refusal, but the model sometimes still cited a source —
because FAISS always returns its top-k regardless of whether anything
is actually relevant, and an alphabetical back-of-book index page (a
dense list of "term, page number" entries) shares enough generic
vocabulary with almost any query to rank deceptively high. The same
failure mode as phase 4's bibliography problem, but for a different
section type.

Unlike the bibliography filter (a regex heuristic over text content),
this one is exact and free of false-positive risk: every chunk already
carries its chapter label from extraction (phase 1), so excluding a
known non-content section name can't accidentally exclude real
chemistry content.
"""

STRUCTURAL_CHAPTERS = frozenset(
    {
        "Front Matter",
        "Table of Contents",
        "Index",
        "Acknowledgments",
        "Preface",
        "Foreword",
        "References",
    }
)


def is_structural_section(chapter: str | None) -> bool:
    return chapter in STRUCTURAL_CHAPTERS
