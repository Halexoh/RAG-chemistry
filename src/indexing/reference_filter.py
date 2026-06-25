"""Heuristic filter for bibliography/reference-list chunks.

Phase 3 (embeddings) found that pure similarity search surfaces
reference-list chunks ahead of substantive content: a list of citations
repeating a topic's name, years, and journal abbreviations can look
deceptively similar to a query about that same topic, even though it
carries no explanatory content.

Rather than deleting this text from the corpus, it's excluded only at
index-build time — chunks.jsonl/embeddings.npy stay complete and
unfiltered; only the search index leaves these out. That keeps the
filter reversible if the heuristic turns out to be wrong.

Signal: a numbered reference list reliably has both (a) several lines
starting with "N. " followed by a capitalized author name, and (b)
several citation years in parentheses, e.g. "(1986)". Tuned against
real chunks from the two books loaded so far (see docs/04-indexacion.md
for the actual examples) — not a universal rule, revisit if a future
book's reference style differs enough to evade it.
"""

import re

PAREN_YEAR_RE = re.compile(r"\(\d{4}\)")
NUMBERED_LINE_RE = re.compile(r"(?m)^\s*\d{1,3}\.\s+[A-Z]")

MIN_PAREN_YEARS = 2
MIN_NUMBERED_LINES = 2


def is_bibliography_like(text: str) -> bool:
    paren_years = len(PAREN_YEAR_RE.findall(text))
    numbered_lines = len(NUMBERED_LINE_RE.findall(text))
    return paren_years >= MIN_PAREN_YEARS and numbered_lines >= MIN_NUMBERED_LINES
