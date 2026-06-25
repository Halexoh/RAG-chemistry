from src.indexing.structural_filter import is_structural_section


def test_known_structural_sections_are_flagged():
    assert is_structural_section("Index") is True
    assert is_structural_section("Table of Contents") is True
    assert is_structural_section("front_matter") is True


def test_real_chapters_are_not_flagged():
    assert is_structural_section("5. Corrosion Failures") is False
    assert is_structural_section("7") is False
    assert is_structural_section("Introduction") is False


def test_none_is_not_flagged():
    assert is_structural_section(None) is False
