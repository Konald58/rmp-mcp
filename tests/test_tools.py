import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from rmp_mcp import client, server
from tests.conftest import NAU, PROFS, USF, sid, tid


async def test_search_school_returns_campuses_best_first(fake_rmp):
    r = await server.search_school("South Florida")
    assert r["found"]
    assert r["best"]["school_id"] == USF
    assert r["best"]["rmp_url"].endswith("/school/1262")
    assert len(r["schools"]) == 5
    counts = [s["num_ratings"] for s in r["schools"]]
    assert counts == sorted(counts, reverse=True)
    assert r["schools"][1]["city"] is None


async def test_search_school_not_found(fake_rmp):
    assert await server.search_school("Hogwarts") == {
        "found": False, "query": "Hogwarts", "schools": []
    }  # fmt: skip


async def test_search_professor_ambiguous_lists_candidates(fake_rmp):
    r = await server.search_professor("Smith", USF)
    assert r["found"] and r["ambiguous"]
    assert r["professor"]["name"] == "Tom Smith"
    assert [c["name"] for c in r["candidates"]] == ["Tom Smith", "Dean Smith", "Joel Smith"]
    assert "Several" in r["note"]
    assert fake_rmp.calls[0][1] == {"text": "Smith", "schoolID": USF}


async def test_search_professor_full_name_resolves(fake_rmp):
    r = await server.search_professor("Joel Smith", USF)
    assert r["found"] and not r["ambiguous"] and "candidates" not in r
    assert r["professor"]["tier"] == "great"
    assert r["professor"]["rmp_url"] == "https://www.ratemyprofessors.com/professor/3"


async def test_search_professor_wrong_initial_is_not_found(fake_rmp):
    r = await server.search_professor("Bob Lee", USF)
    assert not r["found"]
    assert "first" in r["tip"]
    assert r["similar"] == ["Alisa Lee"]


async def test_search_professor_unknown_first_name_is_flagged(fake_rmp):
    r = await server.search_professor("John Smith", USF)
    assert r["found"] and r["ambiguous"]
    assert r["professor"]["name"] == "Joel Smith"
    assert "exactly that first name" in r["note"]


async def test_search_professor_scoped_to_school(fake_rmp):
    r = await server.search_professor("Smith", NAU)
    assert r["professor"]["name"] == "Neal Smith" and not r["ambiguous"]


async def test_search_professor_accepts_numeric_school_id_and_url(fake_rmp):
    for school in ["1364", "https://www.ratemyprofessors.com/school/1364"]:
        r = await server.search_professor("Neal Smith", school)
        assert r["professor"]["name"] == "Neal Smith"


async def test_search_professor_bad_school_id_is_a_tool_error(fake_rmp):
    with pytest.raises(ToolError, match="rejected the request: invalid base64"):
        await server.search_professor("Smith", sid(999))


async def test_search_professor_not_found_suggests_similar(fake_rmp):
    r = await server.search_professor("Smit", USF)
    assert not r["found"] and "Tom Smith" in r["similar"]


async def test_search_professor_blank_input(fake_rmp):
    r = await server.search_professor("   ", USF)
    assert not r["found"] and "last name" in r["tip"]
    assert fake_rmp.calls == []


async def test_null_rating_professor_formats_cleanly(fake_rmp):
    r = await server.search_professor("Nobody", USF)
    p = r["professor"]
    assert p["rating"] is None and p["tier"] == "unrated"
    assert p["would_take_again_pct"] is None
    assert p["name"] == "New Nobody"


async def test_get_professor_details(fake_rmp):
    r = await server.get_professor_details(tid(1))
    assert r["found"] and r["untrusted_content"] is True
    assert r["professor"]["name"] == "Kenneth Mitchell"
    assert r["distribution"] == {
        "total": 42, "awesome_5": 15, "great_4": 15, "good_3": 7, "ok_2": 3, "awful_1": 2
    }  # fmt: skip
    review = r["recent_reviews"][0]
    assert review["class"] == "ACG2021" and review["date"] == "2026-04-02"
    assert len(review["comment"]) == server.MAX_COMMENT_CHARS


@pytest.mark.parametrize("pid", ["1", " 1 ", "https://www.ratemyprofessors.com/professor/1"])
async def test_get_professor_details_accepts_numeric_id_and_url(fake_rmp, pid):
    r = await server.get_professor_details(pid)
    assert r["found"] and fake_rmp.calls[0][1] == {"id": tid(1)}


async def test_get_professor_details_unknown(fake_rmp):
    r = await server.get_professor_details("999")
    assert r == {"found": False, "professor_id": "999", "tip": "Unknown professor id."}


async def test_compare_professors_ranks_flags_and_dedupes(fake_rmp):
    r = await server.compare_professors(["Lee", "lee", "Mitchell", "Nobody", "Ghost"], USF)
    assert [x["professor"]["name"] for x in r["ranked"]] == [
        "Alisa Lee", "Kenneth Mitchell", "New Nobody"
    ]  # fmt: skip
    assert r["ranked"][1]["ambiguous"] is True
    assert r["not_found"] == ["Ghost"]
    assert r["summary"].startswith("Best pick: Alisa Lee (4.6/5, 90% would take again, 30 ratings)")
    assert "ambiguous" in r["summary"]
    assert "errors" not in r
    assert len([c for c in fake_rmp.calls if c[1].get("text") == "Lee"]) == 1


async def test_compare_professors_partial_failure_is_reported(fake_rmp):
    fake_rmp.fail_letters.add("Mitchell")
    r = await server.compare_professors(["Lee", "Mitchell"], USF)
    assert [x["professor"]["name"] for x in r["ranked"]] == ["Alisa Lee"]
    assert r["errors"] == [
        {"query": "Mitchell", "error": "Couldn't reach Rate My Professors. Please try again later."}
    ]


async def test_compare_professors_only_unrated(fake_rmp):
    r = await server.compare_professors(["Nobody"], USF)
    assert r["summary"] == "Matches found but none has ratings yet."


async def test_compare_professors_empty_after_dedupe(fake_rmp):
    with pytest.raises(ToolError, match="at least one name"):
        await server.compare_professors(["  "], USF)
    r = await server.compare_professors(["Ghost"], USF)
    assert r["ranked"] == [] and r["summary"] == "No results found."


async def test_get_top_professors_sweeps_alphabet_and_filters(fake_rmp):
    r = await server.get_top_professors(USF, department="Account", min_ratings=10)
    assert len(fake_rmp.calls) == 26
    assert {c[1]["text"] for c in fake_rmp.calls} == set("abcdefghijklmnopqrstuvwxyz")
    assert [p["name"] for p in r["professors"]] == ["Kenneth Mitchell", "Tom Smith"]
    assert r["sampled"] == len(PROFS)
    assert r["count"] == 2 and "failed" not in r["note"]


async def test_get_top_professors_partial_failure_noted(fake_rmp):
    fake_rmp.fail_letters.update({"a", "b"})
    r = await server.get_top_professors(USF, min_ratings=1)
    assert "2 of 26 searches failed" in r["note"]
    assert r["professors"]


async def test_get_top_professors_total_failure_is_a_tool_error(fake_rmp):
    fake_rmp.fail_letters.update("abcdefghijklmnopqrstuvwxyz")
    with pytest.raises(ToolError, match="Couldn't reach"):
        await server.get_top_professors(USF)


async def test_get_top_professors_empty_note(fake_rmp):
    r = await server.get_top_professors(USF, department="Underwater Basket Weaving")
    assert r["professors"] == [] and "broader" in r["note"]


async def test_tools_are_registered_with_read_only_annotations():
    async with Client(server.mcp) as c:
        tools = {t.name: t for t in await c.list_tools()}
    assert set(tools) == {t.__name__ for t in server.TOOLS}
    for t in tools.values():
        assert t.annotations.readOnlyHint is True
        assert t.annotations.openWorldHint is True


async def test_tool_call_through_mcp_protocol(fake_rmp):
    async with Client(server.mcp) as c:
        result = await c.call_tool("search_school", {"university_name": "South Florida"})
    assert result.data["best"]["name"] == "University of South Florida"


async def test_input_validation_through_mcp_protocol(fake_rmp):
    async with Client(server.mcp) as c:
        with pytest.raises(ToolError):
            await c.call_tool("get_top_professors", {"school_id": USF, "min_ratings": -5})
        with pytest.raises(ToolError):
            await c.call_tool("compare_professors", {"professor_names": [], "school_id": USF})
        with pytest.raises(ToolError):
            await c.call_tool(
                "compare_professors",
                {"professor_names": [f"P{i}" for i in range(11)], "school_id": USF},
            )
        with pytest.raises(ToolError):
            await c.call_tool("search_professor", {"professor_name": "", "school_id": USF})


async def test_rmp_error_through_mcp_protocol_is_user_safe(monkeypatch):
    async def boom(query, variables):
        raise client.RMPError("Couldn't reach Rate My Professors. Please try again later.")

    monkeypatch.setattr(client, "gql", boom)
    async with Client(server.mcp) as c:
        with pytest.raises(ToolError, match="Couldn't reach Rate My Professors") as exc:
            await c.call_tool("search_school", {"university_name": "x"})
    assert "Traceback" not in str(exc.value)


async def test_unexpected_exception_through_mcp_protocol_is_masked(monkeypatch):
    async def weird(query, variables):
        return {"data": {"newSearch": {"schools": {"edges": [{"node": {"name": "No id"}}]}}}}

    monkeypatch.setattr(client, "gql", weird)
    async with Client(server.mcp) as c:
        with pytest.raises(ToolError) as exc:
            await c.call_tool("search_school", {"university_name": "x"})
    assert "KeyError" not in str(exc.value) and "'id'" not in str(exc.value)
