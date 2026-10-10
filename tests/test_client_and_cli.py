import asyncio

import httpx
import pytest

from rmp_mcp import __version__, client, server
from tests.conftest import sid, tid

REAL_ASYNC_CLIENT = httpx.AsyncClient


def _patch_http(monkeypatch, handler):
    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
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
        (lambda r: httpx.Response(200, json=[1, 2]), "unexpected response"),
        (lambda r: httpx.Response(200, json=None), "unexpected response"),
        (
            lambda r: httpx.Response(200, json={"data": None, "errors": [{"message": "bad id"}]}),
            "rejected the request: bad id",
        ),
        (lambda r: httpx.Response(200, json={"errors": ["?"]}), "rejected the request. Check"),
    ],
)
async def test_gql_http_json_and_graphql_errors(monkeypatch, make_response, match):
    _patch_http(monkeypatch, make_response)
    with pytest.raises(client.RMPError, match=match):
        await client.gql("q", {})


async def test_gql_errors_with_data_pass_through(monkeypatch):
    payload = {"data": {"node": None}, "errors": [{"message": "invalid base64"}]}
    _patch_http(monkeypatch, lambda r: httpx.Response(200, json=payload))
    assert await client.gql("q", {}) == payload


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


async def test_gql_concurrency_is_exactly_capped(monkeypatch):
    state = {"inflight": 0, "max": 0}

    async def slow(request):
        state["inflight"] += 1
        state["max"] = max(state["max"], state["inflight"])
        await asyncio.sleep(0.01)
        state["inflight"] -= 1
        return httpx.Response(200, json={"data": {}})

    _patch_http(monkeypatch, slow)
    await asyncio.gather(*(client.gql("q", {"i": i}) for i in range(20)))
    assert state["max"] == client.MAX_INFLIGHT


def test_semaphore_is_rebuilt_per_loop_and_holds_no_loop_reference():
    loops = []
    sems = []
    for _ in range(2):
        loop = asyncio.new_event_loop()
        sems.append(loop.run_until_complete(_grab()))
        loops.append(loop)
        loop.close()
    assert sems[0] is not sems[1]
    assert client._sem_cache is not None and client._sem_cache[0]() is loops[1]


async def _grab():
    return client._semaphore()


def test_id_helpers():
    assert client.numeric_id(tid(123)) == "123"
    assert client.numeric_id("not base64!!") is None
    assert client.numeric_id("YWJj") is None  # "abc", no numeric tail
    assert client.teacher_graphql_id(" 123 ") == tid(123)
    assert client.teacher_graphql_id(tid(5)) == tid(5)
    assert client.teacher_graphql_id("https://www.ratemyprofessors.com/professor/77?x=1") == tid(77)
    assert client.teacher_graphql_id("²") == "²"  # unicode digit is not an id
    assert client.school_graphql_id("1262") == sid(1262)
    assert client.school_graphql_id("https://www.ratemyprofessors.com/school/1262") == sid(1262)
    assert client.professor_url(tid(9)) == "https://www.ratemyprofessors.com/professor/9"
    assert client.professor_url("zzz") == "https://www.ratemyprofessors.com"
    assert client.school_url("zzz") == "https://www.ratemyprofessors.com"


async def test_edges_tolerates_malformed_shapes(monkeypatch):
    async def weird(query, variables):
        return {"data": {"newSearch": {"teachers": None}}}

    monkeypatch.setattr(client, "gql", weird)
    assert await client.search_teachers("x", "y") == []

    async def no_node(query, variables):
        return {"data": {"node": {"name": "missing id"}}}

    monkeypatch.setattr(client, "gql", no_node)
    assert await client.teacher_details("x") is None


def test_cli_defaults_to_stdio(monkeypatch):
    calls = []
    monkeypatch.setattr(server.mcp, "run", lambda *a, **k: calls.append((a, k)))
    server.main([])
    assert calls == [((), {})]


def test_cli_http_defaults_to_loopback(monkeypatch):
    calls = []
    monkeypatch.setattr(server.mcp, "run", lambda *a, **k: calls.append((a, k)))
    server.main(["--transport", "http"])
    assert calls == [((), {"transport": "http", "host": "127.0.0.1", "port": 8000})]


def test_cli_http_non_loopback_warns(monkeypatch, caplog):
    monkeypatch.setattr(server.mcp, "run", lambda *a, **k: None)
    with caplog.at_level("WARNING"):
        server.main(["--transport", "http", "--host", "0.0.0.0", "--port", "9000"])
    assert "exposes an unauthenticated endpoint" in caplog.text


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        server.main(["--version"])
    assert exc.value.code == 0
    assert f"rmp-mcp {__version__}" in capsys.readouterr().out


def test_root_shim_imports_main():
    import importlib.util
    import pathlib

    shim = pathlib.Path(__file__).resolve().parents[1] / "server.py"
    spec = importlib.util.spec_from_file_location("rmp_shim", shim)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main is server.main
