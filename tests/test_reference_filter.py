from src.indexing.reference_filter import is_bibliography_like

# Real chunk excerpts from the loaded books, used to tune the heuristic.
NUMBERED_REFERENCE_LIST = """–10, p. 4.
8. B.F. Goodrich Chemical Company, Latex Bulletin L–19, p. 12.
9. R. A. Heckman, J. Prot. Coat. Linings, 3. 10 (1986).
10. J. E. Fitzwater, Jr., J. Water-Borne Coat., 8, 3 (1985).
11. J. E. Fitzwater, Jr., J. Water-Borne Coat., 7, 3 (1984).
12. G. Pollano and A. Lurier, J. Water-Borne Coat., 9, 1 (1986)."""

CHEMISTRY_CONTENT_WITH_A_CITED_NUMBER = """They
also have good radiation resistance.
16.3
Commercial Information
Several commercially available aromatic polyimides, such as Kapton (DuPont), IP-2080 (Dow), Matrimid
5218 (Ciba-Geigy), Ultem (General Electric), and LARC-TPI (Mitsui-Toatsu chemicals), are used in the
form of films, moldings, adhesives, and composite matrices."""

HISTORICAL_TIMELINE_WITH_BARE_YEARS = """corrosiveness
and corrodibility
Boyle
1763
Bimetallic corrosion
HMS Alarm report
1788
Water becomes alkaline during corrosion
of iron
Austin
1791"""


def test_numbered_reference_list_is_flagged():
    assert is_bibliography_like(NUMBERED_REFERENCE_LIST) is True


def test_content_mentioning_a_product_code_is_not_flagged():
    assert is_bibliography_like(CHEMISTRY_CONTENT_WITH_A_CITED_NUMBER) is False


def test_timeline_with_bare_years_is_not_flagged():
    # Years without parentheses shouldn't trip the citation-year signal.
    assert is_bibliography_like(HISTORICAL_TIMELINE_WITH_BARE_YEARS) is False


def test_empty_text_is_not_flagged():
    assert is_bibliography_like("") is False
