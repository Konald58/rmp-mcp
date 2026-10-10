from rmp_mcp.matching import ParsedName, match_professors, parse_name, search_text
from tests.conftest import PROFS


def test_parse_last_only():
    assert parse_name("Smith") == ParsedName(last_name="Smith")


def test_parse_initial_first():
    assert parse_name("J. Smith") == ParsedName(last_name="Smith", first_initial="J")
    assert parse_name("j smith") == ParsedName(last_name="smith", first_initial="J")


def test_parse_full_name_drops_middle_initials_and_names():
    assert parse_name("John Smith") == ParsedName("Smith", "John", "J")
    assert parse_name("John A. Smith") == ParsedName("Smith", "John", "J")
    assert parse_name("Dr. John A. Smith") == ParsedName("Smith", "John", "J")
    assert parse_name("John Michael Smith") == ParsedName("Michael Smith", "John", "J")


def test_parse_comma_forms_honorifics_and_suffixes():
    assert parse_name("Smith, John") == ParsedName("Smith", "John", "J")
    assert parse_name("Smith, John, Jr.") == ParsedName("Smith", "John", "J")
    assert parse_name("John Smith, Jr.") == ParsedName("Smith", "John", "J")
    assert parse_name("John Smith, PhD") == ParsedName("Smith", "John", "J")
    assert parse_name("Smith, Jr.") == ParsedName("Smith")
    assert parse_name("Dr. Jennifer Smith-Garvin PhD") == ParsedName(
        "Smith-Garvin", "Jennifer", "J"
    )


def test_parse_multiword_last_name_and_accented_initial():
    assert parse_name("Ana Armenta Vega") == ParsedName("Armenta Vega", "Ana", "A")
    assert parse_name("É. Smith") == ParsedName("Smith", first_initial="É")


def test_parse_garbage():
    for text in ["", "   ", ", ", "Jr.", "Dr."]:
        assert parse_name(text) is None


def test_search_text_is_last_word():
    assert search_text(parse_name("Ana Armenta Vega")) == "Vega"
    assert search_text(parse_name("Smith-Garvin")) == "Smith-Garvin"


def test_match_requires_last_name():
    r = match_professors(PROFS, parse_name("Smit"))
    assert r.best is None and r.candidates == () and not r.ambiguous


def test_match_last_name_only_is_ambiguous_and_ranked_by_ratings():
    r = match_professors(PROFS, parse_name("Smith"))
    assert r.ambiguous and not r.first_name_mismatch
    assert [p["firstName"] for p in r.candidates] == ["Tom", "Dean", "Joel"]


def test_match_exact_first_name_resolves():
    r = match_professors(PROFS, parse_name("Joel Smith"))
    assert not r.ambiguous and r.best["firstName"] == "Joel" and len(r.candidates) == 1


def test_match_initial_narrows_but_stays_ambiguous_when_shared():
    r = match_professors(PROFS, parse_name("K. Mitchell"))
    assert r.ambiguous
    assert {p["firstName"] for p in r.candidates} == {"Kenneth", "Kimberly"}


def test_match_initial_resolves_when_unique():
    r = match_professors(PROFS, parse_name("T. Smith"))
    assert not r.ambiguous and r.best["firstName"] == "Tom"


def test_match_wrong_initial_never_returns_a_professor():
    for q in ["B. Lee", "Bob Lee", "Z. Smith", "Zed Smith"]:
        r = match_professors(PROFS, parse_name(q))
        assert r.best is None and r.first_name_mismatch, q


def test_match_unknown_first_name_with_matching_initial_is_flagged():
    r = match_professors(PROFS, parse_name("John Smith"))
    assert r.best["firstName"] == "Joel"
    assert r.ambiguous and r.first_name_mismatch
    assert [p["firstName"] for p in r.candidates] == ["Joel"]


def test_match_middle_name_falls_back_to_final_token():
    r = match_professors(PROFS, parse_name("Alisa Marie Lee"))
    assert r.best["firstName"] == "Alisa" and not r.ambiguous


def test_match_hyphen_apostrophe_and_accent_insensitive():
    assert match_professors(PROFS, parse_name("smith-garvin")).best["lastName"] == "Smith-Garvin"
    assert match_professors(PROFS, parse_name("O'Brien")).best["firstName"] == "Sean"
    assert match_professors(PROFS, parse_name("Jose Garcia")).best["firstName"] == "José"
    assert match_professors(PROFS, parse_name("Smith Garvin")).best is None
