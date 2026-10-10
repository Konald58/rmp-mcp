import pytest

from rmp_mcp import client, server
from tests.conftest import USF, tid


async def test_search_school_returns_campuses_best_first(fake_rmp):
    r = await server.search_school("South Florida")
    assert r["found"]
    assert r["best"]["school_id"] == USF
    assert r["best"]["rmp_url"].endswith("/school/1262")
    assert len(r["schools"]) == 5
    assert [s["num_ratings"] for s in r["schools"]] == sorted(
        [s["num_ratings"] for s in r["schools"]], reverse=True
    )
    assert r["schools"][1]["city"] is None


async def test_search_school_not_found(fake_rmp):
    r = await server.search_school("Hogwarts")
    assert r == {"found": False, "query": "Hogwarts", "schools": []}


async def test_search_professor_ambiguous_lists_candidates(fake_rmp):
    r = await server.search_professor("Smith", USF)
    assert r["found"] and r["ambiguous"]
    assert r["professor"]["name"] == "Tom Smith"
    assert [c["name"] for c in r["candidates"]] == ["Tom Smith", "Joel Smith"]
    assert "note" in r
    # Only the last name is sent to RMP, never the full string.
    assert fake_rmp.calls[0][1] == {"text": "Smith", "schoolID": USF}


async def test_search_professor_full_name_resolves(fake_rmp):
    r = await server.search_professor("Joel Smith", USF)
    assert r["found"] and not r["ambiguous"]
    assert r["professor"]["tier"] == "great"
    assert r["professor"]["rmp_url"] == "https://www.ratemyprofessors.com/professor/3"
    assert "candidates" not in r


async def test_search_professor_not_found_suggests_similar(fake_rmp):
    r = await server.search_professor("Smit", USF)
    assert not r["found"]
    assert "Tom Smith" in r["similar"] or "Joel Smith" in r["similar"]


async def test_search_professor_bad_input(fake_rmp):
    r = await server.search_professor("   ", USF)
    assert not r["found"] and "last name" in r["tip"]
    assert fake_rmp.calls == []


async def test_null_rating_professor_formats_cleanly(fake_rmp):
    r = await server.search_professor("Nobody", USF)
    assert r["professor"]["rating"] is None
    assert r["professor"]["tier"] == "unrated"
    assert r["professor"]["would_take_again_pct"] == 0


async def test_get_professor_details_by_graphql_id(fake_rmp):
    r = await server.get_professor_details(tid(1))
    assert r["found"]
    assert r["professor"]["name"] == "Kenneth Mitchell"
    assert r["distribution"] == {
        "total": 42,
        "awesome_5": 15,
        "great_4": 15,
        "good_3": 7,
        "ok_2": 3,
        "awful_1": 2,
    }
    assert r["recent_reviews"][0]["class"] == "ACG2021"
    assert r["recent_reviews"][0]["date"] == "2026-04-02"
    assert r["recent_reviews"][0]["quality"] == 5


async def test_get_professor_details_by_numeric_id(fake_rmp):
    r = await server.get_professor_details("1")
    assert r["found"]
    assert fake_rmp.calls[0][1] == {"id": tid(1)}


async def test_get_professor_details_unknown(fake_rmp):
    r = await server.get_professor_details("999")
    assert r == {"found": False, "professor_id": "999", "tip": "Unknown professor id."}


async def test_compare_professors_ranks_and_flags(fake_rmp):
    r = await server.compare_professors(["Lee", "Mitchell", "Nobody", "Ghost"], USF)
    names = [x["professor"]["name"] for x in r["ranked"]]
    assert names == ["Alisa Lee", "Kenneth Mitchell", "New Nobody"]
    assert r["ranked"][1]["ambiguous"] is True
    assert r["not_found"] == ["Ghost"]
    assert r["summary"].startswith("Best pick: Alisa Lee (4.6/5")
    assert "ambiguous" in r["summary"]


async def test_compare_professors_empty(fake_rmp):
    r = await server.compare_professors(["Ghost"], USF)
    assert r["ranked"] == [] and r["summary"] == "No results found."


async def test_get_top_professors_sweeps_alphabet_and_filters(fake_rmp):
    r = await server.get_top_professors(USF, department="Account", min_ratings=10)
    assert len(fake_rmp.calls) == 26
    assert {c[1]["text"] for c in fake_rmp.calls} == set("abcdefghijklmnopqrstuvwxyz")
    assert [p["name"] for p in r["professors"]] == ["Kenneth Mitchell", "Tom Smith"]
    assert r["sampled"] == 7
    assert r["count"] == 2


async def test_get_top_professors_empty_note(fake_rmp):
    r = await server.get_top_professors(USF, department="Underwater Basket Weaving")
    assert r["professors"] == [] and "broader" in r["note"]


async def test_tools_are_registered_with_read_only_annotations():
    from fastmcp import Client

    async with Client(server.mcp) as c:
        tools = {t.name: t for t in await c.list_tools()}
    assert set(tools) == {
        "search_school",
        "search_professor",
        "get_professor_details",
        "compare_professors",
        "get_top_professors",
    }
    for t in tools.values():
        assert t.annotations.readOnlyHint is True
        assert t.annotations.openWorldHint is True


async def test_tool_call_through_mcp_protocol(fake_rmp):
    from fastmcp import Client

    async with Client(server.mcp) as c:
        result = await c.call_tool("search_school", {"university_name": "South Florida"})
    assert result.data["best"]["name"] == "University of South Florida"


async def test_rmp_error_from_tool_surfaces_user_safe_message(monkeypatch):
    async def boom(query, variables):
        raise client.RMPError("Couldn't reach Rate My Professors. Please try again later.")

    monkeypatch.setattr(client, "gql", boom)
    with pytest.raises(client.RMPError, match="Couldn't reach"):
        await server.search_school("x")
