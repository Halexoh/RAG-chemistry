from src.extraction.chapters import chapter_from_filename, chapter_map_from_toc


def test_chapter_from_filename_extracts_number():
    assert chapter_from_filename("44044ch7.pdf") == "7"
    assert chapter_from_filename("44044ch72.pdf") == "72"


def test_chapter_from_filename_returns_none_for_non_chapter_files():
    assert chapter_from_filename("44044fm.pdf") is None


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
