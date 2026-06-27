from pathlib import Path

from src.extraction.run import (
    BookSource,
    StandaloneSource,
    book_title_from_bracket_folder,
    clean_category_segment,
    discover_sources,
    is_book_folder,
)


def test_is_book_folder_recognizes_bracket_convention(tmp_path):
    book_dir = tmp_path / "[Forsgren_2006]_Corrosion_Control_Through_Organic_Coatings"
    book_dir.mkdir()
    assert is_book_folder(book_dir) is True


def test_is_book_folder_rejects_plain_category_names(tmp_path):
    category_dir = tmp_path / "Aditivos"
    category_dir.mkdir()
    assert is_book_folder(category_dir) is False


def test_book_title_from_bracket_folder_extracts_author_and_year():
    title = book_title_from_bracket_folder("[Forsgren_2006]_Corrosion_Control_Through_Organic_Coatings")
    assert title == "Corrosion Control Through Organic Coatings (Forsgren, 2006)"


def test_book_title_from_bracket_folder_handles_hyphenated_author_code():
    title = book_title_from_bracket_folder("[MIL-HDBK-1110_1995]_Handbook_for_Paints_and_Protective_Coatings")
    assert title == "Handbook for Paints and Protective Coatings (MIL-HDBK-1110, 1995)"


def test_book_title_from_bracket_folder_falls_back_to_raw_name_when_unmatched():
    assert book_title_from_bracket_folder("Aditivos") == "Aditivos"


def test_clean_category_segment_strips_numeric_prefix_and_underscores():
    assert clean_category_segment("01_Corrosion_y_Proteccion") == "Corrosion y Proteccion"
    assert clean_category_segment("Aditivos") == "Aditivos"


def test_discover_sources_classifies_book_folder_as_one_book(tmp_path):
    book_dir = tmp_path / "[Weldon_2002]_Failure_Analysis_of_Paints_and_Coatings"
    book_dir.mkdir()
    (book_dir / "Cap_01_Intro.pdf").touch()
    (book_dir / "Cap_02_Pigmentos.pdf").touch()

    sources = discover_sources(tmp_path)

    assert len(sources) == 1
    assert isinstance(sources[0], BookSource)
    assert sources[0].title == "Failure Analysis of Paints and Coatings (Weldon, 2002)"
    assert len(sources[0].pdf_files) == 2
    assert sources[0].category == ""


def test_discover_sources_classifies_loose_pdf_as_standalone_document(tmp_path):
    category_dir = tmp_path / "03_Materias_Primas" / "Aditivos"
    category_dir.mkdir(parents=True)
    (category_dir / "BYK_L-AG_1_7_EN.pdf").touch()

    sources = discover_sources(tmp_path)

    assert len(sources) == 1
    assert isinstance(sources[0], StandaloneSource)
    assert sources[0].title == "BYK_L-AG_1_7_EN"
    assert sources[0].category == "Materias Primas/Aditivos"


def test_discover_sources_handles_mixed_loose_pdfs_and_nested_book(tmp_path):
    topic_dir = tmp_path / "01_Corrosion_y_Proteccion"
    topic_dir.mkdir()
    (topic_dir / "Some Paper.pdf").touch()
    book_dir = topic_dir / "[Forsgren_2006]_Corrosion_Control_Through_Organic_Coatings"
    book_dir.mkdir()
    (book_dir / "Cap_01_Introduccion.pdf").touch()

    sources = discover_sources(tmp_path)

    standalone = [s for s in sources if isinstance(s, StandaloneSource)]
    books = [s for s in sources if isinstance(s, BookSource)]
    assert len(standalone) == 1
    assert standalone[0].title == "Some Paper"
    assert standalone[0].category == "Corrosion y Proteccion"
    assert len(books) == 1
    assert books[0].category == "Corrosion y Proteccion"


def test_discover_sources_ignores_non_pdf_files(tmp_path):
    category_dir = tmp_path / "11_Admin"
    category_dir.mkdir()
    (category_dir / "notes.docx").touch()
    (category_dir / "budget.xlsx").touch()

    assert discover_sources(tmp_path) == []
