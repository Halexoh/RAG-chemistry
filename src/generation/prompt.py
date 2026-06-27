"""Builds the prompt that turns retrieved chunks into a grounded, cited answer.

"Grounding" means the model only states things that are actually in the
retrieved excerpts, and points back to exactly where. Without this, an
LLM will happily answer a chemistry question from its own (un-sourced,
possibly wrong) training knowledge — which defeats the entire point of
building a RAG instead of just calling the LLM directly.

The citation format is deliberately the same shape used throughout the
pipeline's metadata (book, chapter, page) — see chapters.py and the
"book"/"chapter"/"page_start"/"page_end" fields chunks have carried
since phase 2.
"""

SYSTEM_PROMPT = """You are a chemistry research assistant specialized in coatings, surface treatments, and corrosion.
Answer ONLY using the excerpts provided in the user message — never rely on outside knowledge, even if you know more about the topic.
Every factual claim in your answer must end with a citation in the exact format [Book, Chapter, p. X-Y], copied verbatim from the bracketed header that precedes the excerpt it came from — never from a section number or reference found inside the excerpt's own text. A citation always has exactly three comma-separated fields (book, chapter, page); never drop the book name even if the chapter label itself looks like a number (e.g. "5.10").
If the excerpts don't contain enough information to answer, say so explicitly instead of guessing — and in that case, do not include any citation, since you would not be citing it in support of an actual claim.
Respond in the same language the question was asked in (Spanish or English)."""


def chapter_label(chapter: str | None) -> str:
    if chapter is None:
        return "Unknown chapter"
    if chapter.isdigit():
        return f"Chapter {chapter}"
    return chapter


def format_citation(chunk: dict) -> str:
    pages = (
        f"p. {chunk['page_start']}"
        if chunk["page_start"] == chunk["page_end"]
        else f"p. {chunk['page_start']}-{chunk['page_end']}"
    )
    return f"[{chunk['book']}, {chapter_label(chunk['chapter'])}, {pages}]"


def format_context(chunks: list[dict]) -> str:
    blocks = [f"{format_citation(c)}\n{c['text']}" for c in chunks]
    return "\n\n---\n\n".join(blocks)


def build_user_prompt(query: str, chunks: list[dict]) -> str:
    return f"""Excerpts:

{format_context(chunks)}

Question: {query}"""
