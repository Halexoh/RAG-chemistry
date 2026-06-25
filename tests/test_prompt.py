from src.generation.prompt import build_user_prompt, chapter_label, format_citation


def test_chapter_label_numeric_chapter():
    assert chapter_label("7") == "Chapter 7"


def test_chapter_label_descriptive_title_passes_through():
    assert chapter_label("5. Corrosion Failures") == "5. Corrosion Failures"


def test_chapter_label_none():
    assert chapter_label(None) == "Unknown chapter"


def test_format_citation_single_page():
    chunk = {"book": "Some Book", "chapter": "3", "page_start": 10, "page_end": 10}
    assert format_citation(chunk) == "[Some Book, Chapter 3, p. 10]"


def test_format_citation_page_range():
    chunk = {"book": "Some Book", "chapter": "3", "page_start": 10, "page_end": 12}
    assert format_citation(chunk) == "[Some Book, Chapter 3, p. 10-12]"


def test_build_user_prompt_includes_citation_and_question():
    chunks = [{"book": "Book A", "chapter": "1", "page_start": 1, "page_end": 1, "text": "hello"}]
    prompt = build_user_prompt("what is X?", chunks)

    assert "[Book A, Chapter 1, p. 1]" in prompt
    assert "hello" in prompt
    assert "what is X?" in prompt
