"""Splits a chapter's pages into overlapping, token-sized chunks.

Why tokens and not characters or words: the embedding model and the LLM
both have a budget measured in tokens (BPE sub-word pieces), not
characters. Sizing chunks in tokens is what actually lines up with that
budget — two chunks with the same character count can have very
different token counts depending on how technical/symbol-heavy the text
is (chemical notation tokenizes worse than prose).

Why overlap: a fact or formula can sit right at a chunk boundary. Without
overlap, retrieval could return a chunk that starts or ends mid-thought,
missing the context needed to make sense of it. Overlap means each
boundary appears intact inside at least one chunk.

Why never cross a chapter boundary: a chunk spanning two unrelated
chapters would carry an ambiguous citation (which chapter does this
chunk "belong" to?) and would mix unrelated context in the same
embedding, hurting retrieval precision.
"""

import tiktoken

ENCODING = tiktoken.get_encoding("cl100k_base")

DEFAULT_CHUNK_SIZE = 600
DEFAULT_OVERLAP = 100


def _tokenize_pages(pages: list[dict]) -> tuple[list[int], list[int]]:
    """Concatenates token ids across pages.

    Returns (tokens, page_of_token), where page_of_token[i] is the page
    number the i-th token came from — this is what lets a chunk report
    an accurate page_start/page_end even when it spans multiple pages.
    """
    tokens: list[int] = []
    page_of_token: list[int] = []
    for page in pages:
        text = page["text"]
        if not text:
            continue
        page_tokens = ENCODING.encode(text)
        tokens.extend(page_tokens)
        page_of_token.extend([page["page"]] * len(page_tokens))
    return tokens, page_of_token


def chunk_pages(
    pages: list[dict],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[dict]:
    """Splits the pages of a single chapter into overlapping token chunks.

    `pages` must all belong to the same (book, chapter) and be in page
    order — see chapters.py / extraction/run.py for how that's guaranteed.
    """
    if overlap >= chunk_size:
        raise ValueError(f"overlap ({overlap}) must be smaller than chunk_size ({chunk_size})")
    if not pages:
        return []

    book = pages[0]["book"]
    chapter = pages[0]["chapter"]
    category = pages[0].get("category", "")

    tokens, page_of_token = _tokenize_pages(pages)
    if not tokens:
        return []

    step = chunk_size - overlap
    chunks = []
    start = 0
    chunk_index = 0
    while True:
        end = min(start + chunk_size, len(tokens))
        chunk_token_ids = tokens[start:end]
        chunk_page_range = page_of_token[start:end]
        chunks.append(
            {
                "book": book,
                "chapter": chapter,
                "category": category,
                "page_start": chunk_page_range[0],
                "page_end": chunk_page_range[-1],
                "chunk_index": chunk_index,
                "text": ENCODING.decode(chunk_token_ids),
                "n_tokens": len(chunk_token_ids),
            }
        )
        if end == len(tokens):
            break
        chunk_index += 1
        start += step

    return chunks
