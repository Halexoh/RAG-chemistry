from src.evaluation.metrics import book_hit, citation_is_valid, extract_citations, is_refusal, keyword_hit


def test_keyword_hit_true_when_any_chunk_contains_any_keyword():
    chunks = [{"text": "Polyurea is a fast-curing elastomer."}]
    assert keyword_hit(chunks, ["polyurea", "epoxy"]) is True


def test_keyword_hit_false_when_no_chunk_matches():
    chunks = [{"text": "This is about something unrelated."}]
    assert keyword_hit(chunks, ["polyurea"]) is False


def test_book_hit():
    chunks = [{"book": "Book A"}, {"book": "Book B"}]
    assert book_hit(chunks, "Book B") is True
    assert book_hit(chunks, "Book C") is False


def test_extract_citations_single_page():
    citations = extract_citations("Some claim [Book A, Chapter 3, p. 10].")
    assert citations == [{"book": "Book A", "chapter": "Chapter 3", "page_start": 10, "page_end": 10}]


def test_extract_citations_page_range_and_multiple():
    text = "First [Book A, Chapter 1, p. 5-7]. Second [Book B, Chapter 2, p. 12]."
    citations = extract_citations(text)
    assert len(citations) == 2
    assert citations[0]["page_start"] == 5 and citations[0]["page_end"] == 7
    assert citations[1]["page_start"] == 12 and citations[1]["page_end"] == 12


def test_citation_is_valid_when_overlapping_source_exists():
    citation = {"book": "Book A", "page_start": 10, "page_end": 12}
    sources = [{"book": "Book A", "page_start": 11, "page_end": 11}]
    assert citation_is_valid(citation, sources) is True


def test_citation_is_invalid_when_book_does_not_match():
    citation = {"book": "Book A", "page_start": 10, "page_end": 10}
    sources = [{"book": "Book B", "page_start": 10, "page_end": 10}]
    assert citation_is_valid(citation, sources) is False


def test_citation_is_invalid_when_pages_do_not_overlap():
    citation = {"book": "Book A", "page_start": 10, "page_end": 10}
    sources = [{"book": "Book A", "page_start": 50, "page_end": 55}]
    assert citation_is_valid(citation, sources) is False


def test_is_refusal_detects_known_phrases():
    assert is_refusal("No tengo información suficiente para responder.") is True
    assert is_refusal("Lo siento, pero los fragmentos no contienen eso.") is True
    assert is_refusal("Polyurea is used as a protective coating.") is False
