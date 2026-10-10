from rmp_mcp.matching import ParsedName, match_professors, parse_name
from tests.conftest import PROFS


def test_parse_last_only():
    assert parse_name("Smith") == ParsedName(last_name="Smith")


def test_parse_initial_first():
    assert parse_name("J. Smith") == ParsedName(last_name="Smith", first_initial="J")
    assert parse_name("j smith") == ParsedName(last_name="smith", first_initial="J")


def test_parse_full_name_and_middle():
    assert parse_name("John Smith") == ParsedName("Smith", "John", "J")
    assert parse_name("John A. Smith") == ParsedName("A. Smith", "John", "J")


def test_parse_comma_form_and_honorifics():
    assert parse_name("Smith, John") == ParsedName("Smith", "John", "J")
    assert parse_name("Dr. Jennifer Smith-Garvin PhD") == ParsedName(
        "Smith-Garvin", "Jennifer", "J"
    )


def test_parse_multiword_last_name():
    assert parse_name("Ana Armenta Vega") == ParsedName("Armenta Vega", "Ana", "A")


def test_parse_garbage():
    assert parse_name("") is None
    assert parse_name("   ") is None
    assert parse_name(", ") is None


def test_match_requires_exact_last_name():
    r = match_professors(PROFS, parse_name("Smit"))
    assert r.best is None and r.candidates == () and not r.ambiguous


def test_match_last_name_only_is_ambiguous_and_ranked_by_ratings():
    r = match_professors(PROFS, parse_name("Smith"))
    assert r.ambiguous
    assert [p["firstName"] for p in r.candidates] == ["Tom", "Joel"]
    assert r.best["firstName"] == "Tom"


def test_match_first_name_resolves():
    r = match_professors(PROFS, parse_name("Joel Smith"))
    assert not r.ambiguous
    assert r.best["firstName"] == "Joel"
    assert len(r.candidates) == 1


def test_match_initial_narrows_but_stays_ambiguous_when_several_share_it():
    r = match_professors(PROFS, parse_name("K. Mitchell"))
    assert r.ambiguous
    assert {p["firstName"] for p in r.candidates} == {"Kenneth", "Kimberly"}
    assert r.best["firstName"] == "Kenneth"


def test_match_initial_resolves_when_unique():
    r = match_professors(PROFS, parse_name("T. Smith"))
    assert not r.ambiguous and r.best["firstName"] == "Tom"


def test_match_hyphen_and_case_insensitive():
    r = match_professors(PROFS, parse_name("smith-garvin"))
    assert r.best is not None and r.best["lastName"] == "Smith-Garvin"
    r = match_professors(PROFS, parse_name("Smith Garvin"))
    assert r.best is None  # "Smith" is read as a first name here; last name "Garvin" has no match


def test_match_unknown_first_name_falls_back_to_last_name_set():
    r = match_professors(PROFS, parse_name("Zed Smith"))
    assert r.ambiguous and r.best["firstName"] == "Tom"
