# rmp-mcp 1.0: correctness fixes + universal packaging

Status: done except publish (2026-10-10)

## Why

The server works (verified live at USF, NAU and UCF on 2026-10-09) but has the
wrong-professor bug the extension already fixed, a dead ratings query, no cap on
parallel RMP requests, and is documented and packaged for Claude only.

## Steps

### Correctness
1. [x] `src/rmp_mcp/matching.py`: parse "Smith", "J. Smith", "John Smith",
   "Smith, John"; strict last-name match; first name or initial narrows; return
   best plus candidates plus `ambiguous` flag (port of `lib/scoring.js`).
2. [x] `search_professor` and `compare_professors` use the matcher and never
   silently pick `professors[0]`.
3. [x] New `get_professor_details(professor_id)`: rating distribution plus the
   5 most recent reviews, using the previously dead query.
4. [x] `get_top_professors`: `asyncio.Semaphore(6)`, sweep all 26 letters.
5. [x] `search_school` returns up to 5 campuses with the best first.
6. [x] Drop the "tested at USF only" caveats.

### Universal
7. [x] `pyproject.toml` (`src/` layout, `rmp-mcp` console script, `[dev]`
   extras: pytest, pytest-asyncio, pytest-cov, ruff, bandit, build).
8. [x] `rmp-mcp` CLI: `--transport stdio|http`, `--host`, `--port`.
9. [x] Tool annotations: `readOnlyHint`, `idempotentHint`, `openWorldHint`.
10. [x] Root `server.py` stays as a thin compatibility shim.
11. [x] MIT `LICENSE`, `CHANGELOG.md`, `server.json` for the MCP registry,
    README with one config block per client (Claude Desktop, Claude Code,
    Cursor, Windsurf, VS Code, Gemini CLI, Codex CLI, Zed, ChatGPT via HTTP).
12. [x] Tests in `tests/` with canned GraphQL responses, no live calls; 80%
    coverage; `ruff` and `bandit` clean.
13. [x] Re-register the local Claude Code entry to the `rmp-mcp` console script
    (back up `~/.claude.json` first).
14. [x] Build the wheel locally. PyPI upload and registry submission wait for
    Kon's go.
