# AGENTS.md — rmp-mcp

MCP server that lets Claude search, compare, and rank professors using Rate My Professors data.
Companion to the `rmp-extension` Chrome extension; same public RMP GraphQL endpoint, conversational interface instead of in-page injection.

## Stack

- Python 3.12, single-file server (`server.py`)
- [FastMCP](https://github.com/jlowin/fastmcp) (`fastmcp>=2.0`) for the MCP server/tool decorators
- `httpx` for the RMP GraphQL calls
- No database, no auth, no API key — hits RMP's public GraphQL endpoint directly

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

Register with Claude Code / Desktop:

```bash
claude mcp add-json rmp-mcp '{
  "type": "stdio",
  "command": "/absolute/path/to/rmp-mcp/.venv/bin/python",
  "args": ["/absolute/path/to/rmp-mcp/server.py"]
}'
```

## Test

No automated test suite yet. Manual verification: register the server, then in Claude ask it to search a known school (e.g. "University of South Florida") and a known professor, and confirm the tool calls return data.

## Layout

- `server.py` — the entire server: GraphQL query strings, `_gql` HTTP helper, `RMPError`, and the four `@mcp.tool()` functions
- `requirements.txt` — `fastmcp`, `httpx`
- `.venv/` — local virtualenv, gitignored
- `docs/decisions.md`, `docs/plans/`, `docs/notes/` — project history and working notes

## Tools exposed

- `search_school` — find a school by name → school ID
- `search_professor` — look up a professor at a school
- `compare_professors` — compare multiple professors side by side
- `get_top_professors` — top-rated professors at a school, optionally by department

## Conventions and pitfalls

- Deliberately single-file. Don't split into a package unless the file genuinely outgrows readability — this is a small, focused server.
- `_gql()` is the only place that talks to RMP; all network/HTTP/JSON error handling goes through it and raises `RMPError`. New tools should call `_gql`, not `httpx` directly.
- RMP's GraphQL endpoint is unofficial and undocumented — it can change shape without notice. Verified only against University of South Florida; other schools are expected to work (same endpoint) but are unverified.
- School/professor IDs from RMP are base64-encoded GraphQL node IDs (see `_professor_url`'s `b64decode` usage) — don't assume they're plain integers.
- No LICENSE file yet on this public repo.
