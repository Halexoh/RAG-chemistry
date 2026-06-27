"""Pure, model-free checks used to score each evaluation case.

Kept independent of retrieve()/answer_question() so they can be unit
tested with plain dicts and strings — no FAISS index or LLM call needed
to verify the scoring logic itself is correct.
"""

import re

# Book field allows internal commas (book_title_from_bracket_folder produces
# titles like "Title (Author, 2007)") — only excludes "]" so it still can't
# cross into a different citation's brackets. Chapter field excludes commas,
# since that's what anchors where the book field ends.
CITATION_RE = re.compile(r"\[([^\]]+),\s*([^,\]]+),\s*p\.\s*(\d+)(?:-(\d+))?\]")

# Phrases the model has actually used (see docs/06) when admitting the
# excerpts don't cover a question, in both languages.
REFUSAL_PATTERNS = [
    "no contien",
    "don't contain",
    "does not contain",
    "no encontr",
    "not contain",
    "no information",
    "no hay informaci",
    "insufficient information",
    "no tengo informaci",
    "lo siento",
    "i'm sorry",
    "no se menciona",
    "not enough information",
    "no proporcionan informaci",
]


def keyword_hit(chunks: list[dict], keywords: list[str]) -> bool:
    text = " ".join(c["text"].lower() for c in chunks)
    return any(kw.lower() in text for kw in keywords)


def book_hit(chunks: list[dict], expected_book: str) -> bool:
    return any(c["book"] == expected_book for c in chunks)


def extract_citations(answer: str) -> list[dict]:
    citations = []
    for book, chapter, start, end in CITATION_RE.findall(answer):
        citations.append(
            {
                "book": book.strip(),
                "chapter": chapter.strip(),
                "page_start": int(start),
                "page_end": int(end) if end else int(start),
            }
        )
    return citations


def citation_is_valid(citation: dict, sources: list[dict]) -> bool:
    """A citation is valid if it names a book/page range that overlaps an
    actually-retrieved source — i.e. it wasn't fabricated by the model."""
    for source in sources:
        if source["book"].strip() != citation["book"]:
            continue
        if citation["page_start"] <= source["page_end"] and source["page_start"] <= citation["page_end"]:
            return True
    return False


def is_refusal(answer: str) -> bool:
    lowered = answer.lower()
    return any(pattern in lowered for pattern in REFUSAL_PATTERNS)
