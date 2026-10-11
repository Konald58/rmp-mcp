---
status: active
---

# rmp-mcp

## What it is

An MCP (Model Context Protocol) server that lets any MCP client (Claude, Cursor, VS Code,
Windsurf, Gemini CLI, Codex, Zed, ChatGPT over HTTP) search, compare and rank professors
using Rate My Professors' public GraphQL endpoint. Companion to `rmp-extension`: same data,
conversational interface instead of in-page injection.

## Where it stands (2026-10-10 21:00)

- **1.0.0 pushed and tagged** (`v1.0.0`, GitHub release with wheel and sdist attached). GitHub
  description updated. CI (`test.yml`: ruff, bandit, pytest on 3.10 and 3.12) green.
- **Not on PyPI yet.** Publishing is tokenless via `.github/workflows/publish.yml` (PyPI
  Trusted Publishing, environment `pypi`); the Trusted Publisher entry on pypi.org still has to
  be created, which needs Kon signed in to pypi.org (tab open in Chrome). Then run the
  workflow (Actions tab or `gh workflow run publish.yml`).
- **Not in the MCP registry yet.** `mcp-publisher` 1.8.1 is installed (Homebrew). After PyPI:
  `mcp-publisher login github` (device code, Kon's click) then `mcp-publisher publish` in the
  repo. The README carries `mcp-name: io.github.konald58/rmp-mcp` for the registry's check.
- Package: `src/rmp_mcp/` (`client.py`, `matching.py`, `formatting.py`, `server.py`),
  `rmp-mcp` console script, `--transport stdio|http`, five tools with annotations, strict
  matching ported from the extension, `get_professor_details`, 6-wide request cap. Root
  `server.py` is a shim. 64 tests, 98% coverage. Wheel verified in a clean venv. Local Claude
  Code registration uses `.venv/bin/rmp-mcp`.
- Two fresh-context reviews, all findings fixed. Pre-public-release gates passed on the shipped
  tree.

## Next up

1. Kon signs in to pypi.org; add Trusted Publisher (owner Konald58, repo rmp-mcp, workflow
   publish.yml, environment pypi); run the publish workflow; confirm `pip install rmp-mcp`.
2. `mcp-publisher login github` (Kon's device-code click), then `mcp-publisher publish`.
3. Optional: hosted HTTP transport. Deferred on purpose (no auth, open proxy to RMP).

## Open questions

- Whether to add a `get_school_departments` helper so `get_top_professors` filters can be
  discovered instead of guessed.
