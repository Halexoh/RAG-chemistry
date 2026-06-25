from src.extraction.chapters import chapter_from_filename, chapter_map_from_toc, structural_label_from_filename


def test_chapter_from_filename_extracts_number_suffix_style():
    assert chapter_from_filename("44044ch7.pdf") == "7"
    assert chapter_from_filename("44044ch72.pdf") == "72"


def test_chapter_from_filename_extracts_number_prefix_style():
    assert chapter_from_filename("Ch1  introduction.pdf") == "1"
    assert chapter_from_filename("ch4 blast cleaning and other heavy surface pretreatments.pdf") == "4"
    assert chapter_from_filename("Ch5. abrasive blasting and heavy metal contamination.pdf") == "5"


def test_chapter_from_filename_extracts_underscore_numbered_style():
    assert chapter_from_filename("90725_05a.pdf") == "5"
    assert chapter_from_filename("90725_08d.pdf") == "8"
    assert chapter_from_filename("13372_16.pdf") == "16"


def test_chapter_from_filename_extracts_part_style():
    assert chapter_from_filename("part 1 - paint composition and applications.pdf") == "1"
    assert chapter_from_filename("part10- automotive paints.pdf") == "10"


def test_chapter_from_filename_returns_none_for_non_chapter_files():
    assert chapter_from_filename("44044fm.pdf") is None
    assert chapter_from_filename("An Aspect of Concrete Protection by Surface Coating.pdf") is None


def test_structural_label_from_filename_short_codes():
    assert structural_label_from_filename("13372_fm.pdf") == "Front Matter"
    assert structural_label_from_filename("13372_toc.pdf") == "Table of Contents"
    assert structural_label_from_filename("13372_indx.pdf") == "Index"
    assert structural_label_from_filename("13372_pref.pdf") == "Preface"
    assert structural_label_from_filename("43041_fore.pdf") == "Foreword"
    assert structural_label_from_filename("43041_ref.pdf") == "References"


def test_structural_label_from_filename_full_words_english_and_spanish():
    assert structural_label_from_filename("contents.pdf") == "Table of Contents"
    assert structural_label_from_filename("index.pdf") == "Index"
    assert structural_label_from_filename("Preface.pdf") == "Preface"
    assert structural_label_from_filename("portada.pdf") == "Front Matter"
    assert structural_label_from_filename("prefacio.pdf") == "Preface"
    assert structural_label_from_filename("prefacio 1a edición.pdf") == "Preface"


def test_structural_label_from_filename_distinctive_phrases():
    assert structural_label_from_filename("Author Index.pdf") == "Index"
    assert structural_label_from_filename("Subject Index.pdf") == "Index"
    assert structural_label_from_filename("Copyright, Advisory Board, Foreword.pdf") == "Front Matter"


def test_structural_label_from_filename_keeps_glossary_and_supplement_as_content():
    # Real definitions/content, not pure noise — see structural_filter.py.
    assert structural_label_from_filename("12953_supp.pdf") == "Supplement"
    assert structural_label_from_filename("43041_glo.pdf") == "Glossary"


def test_structural_label_from_filename_none_for_real_titled_chapter():
    assert structural_label_from_filename("An Aspect of Concrete Protection by Surface Coating.pdf") is None


class FakeDoc:
    """Minimal stand-in for fitz.Document — just enough for chapter_map_from_toc."""

    def __init__(self, toc, page_count):
        self._toc = toc
        self.page_count = page_count

    def get_toc(self):
        return self._toc


def test_chapter_map_from_toc_resolves_missing_pages():
    # Level 1 = book title (no real page), level 2 = chapters (some with -1,
    # resolved from a later sibling), level 3 = subsections with real pages.
    toc = [
        [1, "Book Title", -1],
        [2, "Chapter 1", -1],
        [3, "1.1 Intro", 5],
        [2, "Chapter 2", 20],
        [3, "2.1 Intro", 20],
    ]
    page_to_chapter = chapter_map_from_toc(FakeDoc(toc, page_count=30))

    assert page_to_chapter[4] == "Chapter 1"  # page 5 is 0-indexed as 4
    assert page_to_chapter[19] == "Chapter 2"
    assert page_to_chapter[29] == "Chapter 2"  # last page belongs to last chapter


def test_chapter_map_from_toc_returns_empty_dict_when_no_toc():
    assert chapter_map_from_toc(FakeDoc([], page_count=10)) == {}
