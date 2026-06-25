import pytest

from src.chunking.chunker import chunk_pages


def make_page(book="Book", chapter="1", page=1, text="word ") -> dict:
    return {"book": book, "chapter": chapter, "page": page, "text": text}


def test_short_page_produces_a_single_chunk():
    page = make_page(text="hola mundo, esto es una prueba corta")
    chunks = chunk_pages([page], chunk_size=600, overlap=100)

    assert len(chunks) == 1
    assert chunks[0]["page_start"] == 1
    assert chunks[0]["page_end"] == 1
    assert chunks[0]["text"] == page["text"]


def test_long_text_produces_overlapping_chunks():
    long_text = "palabra " * 1000  # comfortably more than one chunk worth of tokens
    page = make_page(text=long_text)
    chunks = chunk_pages([page], chunk_size=600, overlap=100)

    assert len(chunks) > 1
    # consecutive chunks must share text at the boundary (the overlap)
    assert chunks[0]["text"][-50:] in chunks[1]["text"]


def test_page_range_spans_multiple_pages_when_a_chunk_crosses_them():
    pages = [
        make_page(page=1, text="uno " * 400),
        make_page(page=2, text="dos " * 400),
    ]
    chunks = chunk_pages(pages, chunk_size=600, overlap=100)

    spanning = [c for c in chunks if c["page_start"] != c["page_end"]]
    assert spanning, "expected at least one chunk to span page 1 and page 2"


def test_empty_pages_produce_no_chunks():
    assert chunk_pages([]) == []
    assert chunk_pages([make_page(text="")]) == []


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_pages([make_page(text="algo")], chunk_size=100, overlap=100)
