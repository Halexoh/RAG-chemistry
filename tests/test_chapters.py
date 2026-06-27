from src.extraction.chapters import (
    chapter_from_filename,
    chapter_map_from_toc,
    dedupe_versioned_chapters,
    drop_exact_duplicate_files,
    structural_label_from_filename,
    version_suffix,
)


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


def test_chapter_from_filename_extracts_spanish_cap_and_sec_style():
    assert chapter_from_filename("Cap_01_Introduccion.pdf") == "1"
    assert chapter_from_filename("Cap_02_Composicion_del_Recubrimiento_Anticorrosivo.pdf") == "2"
    assert chapter_from_filename("Cap_05a_Tipos_de_Recubrimientos_Parte1.pdf") == "5"
    assert chapter_from_filename("Cap_05b_Tipos_de_Recubrimientos_Parte2.pdf") == "5"
    assert chapter_from_filename("Sec_01_Introduccion.pdf") == "1"
    assert chapter_from_filename("Sec_10_Sistemas_de_Recubrimiento.pdf") == "10"


def test_chapter_from_filename_does_not_false_positive_on_cap_sec_prefix_words():
    # "Capacitor"/"Security" etc. start with "cap"/"sec" but aren't followed
    # by a chapter number — must not be mistaken for "Cap_<N>"/"Sec_<N>".
    assert chapter_from_filename("Capacitor properties of coatings.pdf") is None
    assert chapter_from_filename("Security assessment of pipelines.pdf") is None


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


def test_structural_label_from_filename_underscore_heavy_spanish_names():
    # Same words as the space-separated Spanish tests above, but in the
    # all-underscore convention this personal archive uses throughout.
    assert structural_label_from_filename("00_Portada.pdf") == "Front Matter"
    assert structural_label_from_filename("00_Portada_y_Serie_Editorial.pdf") == "Front Matter"
    assert structural_label_from_filename("00_Prefacio.pdf") == "Preface"
    assert structural_label_from_filename("00_Prefacio_1a_Edicion.pdf") == "Preface"
    assert structural_label_from_filename("00_Prefacio_2a_Edicion.pdf") == "Preface"
    assert structural_label_from_filename("00_Tabla_de_Contenido.pdf") == "Table of Contents"
    assert structural_label_from_filename("00_Tabla_de_Contenido_e_Indice.pdf") == "Table of Contents"
    assert structural_label_from_filename("00_Contenido.pdf") == "Table of Contents"


def test_structural_label_from_filename_zz_prefix_for_trailing_sections():
    assert structural_label_from_filename("ZZ_Indice.pdf") == "Index"
    assert structural_label_from_filename("ZZ_Glosario.pdf") == "Glossary"
    assert structural_label_from_filename("ZZ_Referencias.pdf") == "References"
    assert structural_label_from_filename("ZZ_Directorio_de_Proveedores.pdf") == "Supplement"


def test_version_suffix_extracts_explicit_version_or_defaults_to_one():
    assert version_suffix("Cap_01b_Introduccion_v2.pdf") == 2
    assert version_suffix("Cap_01_Introduccion.pdf") == 1
    assert version_suffix("Cap_07b_Ensayos_Corrosion_Fundamentos_v2.pdf") == 2


def test_dedupe_versioned_chapters_keeps_only_highest_version_when_marked():
    # Forsgren case: an original file plus a "_v2" re-export of the same
    # content — the original should be dropped, not kept alongside it.
    by_chapter = {
        "1": ["Cap_01_Introduccion.pdf", "Cap_01b_Introduccion_v2.pdf"],
    }
    result = dedupe_versioned_chapters(by_chapter)
    assert result["1"] == ["Cap_01b_Introduccion_v2.pdf"]


def test_dedupe_versioned_chapters_keeps_all_genuine_subparts_when_unmarked():
    # Weldon case: "05a"/"05b" are different content (Parte1/Parte2), no
    # "_vN" marker anywhere — nothing should be dropped.
    by_chapter = {
        "5": ["Cap_05a_Tipos_de_Recubrimientos_Parte1.pdf", "Cap_05b_Tipos_de_Recubrimientos_Parte2.pdf"],
    }
    result = dedupe_versioned_chapters(by_chapter)
    assert result["5"] == [
        "Cap_05a_Tipos_de_Recubrimientos_Parte1.pdf",
        "Cap_05b_Tipos_de_Recubrimientos_Parte2.pdf",
    ]


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


def test_chapter_map_from_toc_returns_empty_dict_when_toc_is_pure_navigation_links():
    # A short article PDF whose "TOC" is just navigation bookmarks (a real
    # case found in a personal archive's standalone documents) — every
    # entry sits at page -1 with no sibling anywhere to borrow a page
    # from, so nothing in it is usable as a chapter map.
    toc = [
        [1, "NACE Home Page", -1],
        [1, "FAQs", -1],
        [1, "Search Site", -1],
    ]
    assert chapter_map_from_toc(FakeDoc(toc, page_count=2)) == {}


def test_drop_exact_duplicate_files_removes_byte_identical_copies(tmp_path):
    # Real case: "Sec_11_Miscelaneos.pdf" and "Sec_11b_Miscelaneos_cont.pdf"
    # in the same book — the "_cont" name implies different content, but
    # they were an exact copy-paste accident. No "_vN" marker involved, so
    # dedupe_versioned_chapters() alone wouldn't catch this.
    a = tmp_path / "Sec_11_Miscelaneos.pdf"
    b = tmp_path / "Sec_11b_Miscelaneos_cont.pdf"
    a.write_bytes(b"same content")
    b.write_bytes(b"same content")

    kept = drop_exact_duplicate_files([a, b])

    assert kept == [a]


def test_drop_exact_duplicate_files_keeps_genuinely_different_content(tmp_path):
    a = tmp_path / "Cap_05a_Parte1.pdf"
    b = tmp_path / "Cap_05b_Parte2.pdf"
    a.write_bytes(b"part one content")
    b.write_bytes(b"part two content")

    kept = drop_exact_duplicate_files([a, b])

    assert sorted(kept) == sorted([a, b])
