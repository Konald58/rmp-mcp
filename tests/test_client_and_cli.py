import httpx
import pytest

from rmp_mcp import client, server
from tests.conftest import tid


def _transport(handler):
    return httpx.MockTransport(handler)


REAL_ASYNC_CLIENT = httpx.AsyncClient


def _patch_http(monkeypatch, handler):
    def factory(*args, **kwargs):
        kwargs["transport"] = _transport(handler)
        return REAL_ASYNC_CLIENT(*args, **kwargs)

    monkeypatch.setattr(client.httpx, "AsyncClient", factory)


async def test_gql_success_and_headers(monkeypatch):
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        seen["referer"] = request.headers.get("referer")
        return httpx.Response(200, json={"data": {"ok": True}})

    _patch_http(monkeypatch, handler)
    assert await client.gql("q", {}) == {"data": {"ok": True}}
    assert seen["auth"] is None
    assert seen["referer"] == "https://www.ratemyprofessors.com/"


@pytest.mark.parametrize(
    "make_response, match",
    [
        (lambda r: httpx.Response(503), "HTTP 503"),
        (lambda r: httpx.Response(200, content=b"<html>"), "unexpected response"),
    ],
)
async def test_gql_http_and_json_errors(monkeypatch, make_response, match):
    _patch_http(monkeypatch, make_response)
    with pytest.raises(client.RMPError, match=match):
        await client.gql("q", {})


async def test_gql_timeout_and_connect_errors(monkeypatch):
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    _patch_http(monkeypatch, timeout)
    with pytest.raises(client.RMPError, match="too long"):
        await client.gql("q", {})

    def down(request):
        raise httpx.ConnectError("down", request=request)

    _patch_http(monkeypatch, down)
    with pytest.raises(client.RMPError, match="reach"):
        await client.gql("q", {})


async def test_gql_concurrency_is_capped(monkeypatch):
    import asyncio

    state = {"inflight": 0, "max": 0}

    async def slow(request):
        state["inflight"] += 1
        state["max"] = max(state["max"], state["inflight"])
        await asyncio.sleep(0.01)
        state["inflight"] -= 1
        return httpx.Response(200, json={"data": {}})

    _patch_http(monkeypatch, slow)
    await asyncio.gather(*(client.gql("q", {"i": i}) for i in range(20)))
    assert state["max"] <= client.MAX_INFLIGHT


def test_id_helpers():
    assert client.numeric_id(tid(123)) == "123"
    assert client.numeric_id("not base64!!") is None
    assert client.numeric_id("YWJj") is None  # "abc", no numeric tail
    assert client.teacher_graphql_id(" 123 ") == tid(123)
    assert client.teacher_graphql_id(tid(5)) == tid(5)
    assert client.professor_url(tid(9)) == "https://www.ratemyprofessors.com/professor/9"
    assert client.professor_url("zzz") == "https://www.ratemyprofessors.com"
    assert client.school_url("zzz") == "https://www.ratemyprofessors.com"


async def test_edges_tolerates_malformed_payloads(monkeypatch):
    async def weird(query, variables):
        return {"data": {"newSearch": {"teachers": None}}}

    monkeypatch.setattr(client, "gql", weird)
    assert await client.search_teachers("x", "y") == []

    async def no_data(query, variables):
        return {"errors": [{"message": "nope"}]}

    monkeypatch.setattr(client, "gql", no_data)
    assert await client.search_schools("x") == []
    assert await client.teacher_details("x") is None


def test_cli_defaults_to_stdio(monkeypatch):
    calls = []
    monkeypatch.setattr(server.mcp, "run", lambda *a, **k: calls.append((a, k)))
    server.main([])
    assert calls == [((), {})]


def test_cli_http_transport(monkeypatch):
    calls = []
    monkeypatch.setattr(server.mcp, "run", lambda *a, **k: calls.append((a, k)))
    server.main(["--transport", "http", "--host", "0.0.0.0", "--port", "9000"])
    assert calls == [((), {"transport": "http", "host": "0.0.0.0", "port": 9000})]


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        server.main(["--version"])
    assert exc.value.code == 0
    assert "rmp-mcp 1.0.0" in capsys.readouterr().out
