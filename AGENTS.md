# AGENTS.md — rmp-mcp

MCP server that lets any MCP client (Claude, Cursor, VS Code, Windsurf, Gemini CLI, Codex, Zed,
ChatGPT over HTTP) search, compare and rank professors using Rate My Professors data. Companion to
the `rmp-extension` Chrome extension; same public RMP GraphQL endpoint, conversational interface
instead of in-page injection.

## Stack

- Python 3.10+, `src/` layout, `pyproject.toml` (setuptools), console script `rmp-mcp`
- [FastMCP](https://github.com/jlowin/fastmcp) `>=3,<4` for the server and tool registration
- `httpx` for the RMP GraphQL calls
- No database, no auth, no API key: hits RMP's public GraphQL endpoint directly

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
rmp-mcp                                   # stdio (default)
rmp-mcp --transport http --port 8000      # Streamable HTTP at /mcp, binds 127.0.0.1
```

Local Claude Code registration points at `.venv/bin/rmp-mcp`. Other clients: see README.

## Test

```bash
pytest                    # canned GraphQL responses, no network; 80% coverage gate
ruff check src tests && ruff format --check src tests
bandit -r src
```

Live check (hits RMP): run the tools through `fastmcp.Client` against `server.mcp`, or ask a
registered client to search a known school.

CI (`.github/workflows/test.yml`) runs ruff, bandit and pytest on 3.10 and 3.12. Releases publish to PyPI
via `.github/workflows/publish.yml` (Trusted Publishing, `pypi` environment, no token) on a published
GitHub release or by hand; the registry entry is published afterwards with `mcp-publisher`.

## Layout

- `src/rmp_mcp/client.py` — GraphQL query strings, `gql()` with a 6-wide semaphore per event
  loop and all network/HTTP/JSON error handling (`RMPError`), id helpers (GraphQL id, numeric id
  or RMP URL in; GraphQL id out)
- `src/rmp_mcp/matching.py` — `parse_name` and `match_professors` (strict rules below)
- `src/rmp_mcp/formatting.py` — node-to-dict shaping, `dedupe_names`
- `src/rmp_mcp/server.py` — the five tools, annotations, `main()` CLI
- `server.py` (root) — compatibility shim for pre-1.0 configs; adds `src/` to `sys.path`
- `server.json` — MCP registry manifest; `CHANGELOG.md`; `docs/decisions.md`, `docs/plans/`

## Tools exposed

- `search_school` — name → up to five campuses, best first, with `school_id`
- `search_professor` — one professor; `ambiguous` flag plus `candidates` when several match
- `get_professor_details` — rating distribution and five recent reviews (`untrusted_content`)
- `compare_professors` — up to ten names, concurrent lookups, partial failures reported
- `get_top_professors` — 26-letter search sweep, department filter, `min_ratings` gate

## Conventions and pitfalls

- `client.gql()` is the only place that talks to RMP. New tools call the `client.search_*` /
  `teacher_details` helpers, never `httpx` directly.
- Matching is strict, same as the extension: exact last name; a first initial must match; an
  exact first name wins; several survivors mean `ambiguous: true` with every candidate listed.
  Never return the first search hit silently.
- Tool bodies are wrapped so `RMPError` becomes a `ToolError` with a user-safe message;
  `mask_error_details=True` hides anything else. Do not let raw tracebacks reach clients.
- RMP's endpoint is unofficial: HTTP 200 with `errors` and no `data` is treated as a failure
  (bad `school_id` is the usual cause). Verified at USF, NAU and UCF on 2026-10-09.
- IDs are base64 GraphQL node ids (`Teacher-123`, `School-1262`); helpers accept numeric ids and
  profile URLs so users can paste from the site.
- Review comments, names and departments are public input: capped in length, flagged
  `untrusted_content`, and described as data in the server instructions.
- Files stay under 400 lines; `server.py` is the one to watch when adding tools.
