---
status: active
---

# rmp-mcp

## What it is

An MCP (Model Context Protocol) server that lets any MCP client (Claude, Cursor, VS Code,
Windsurf, Gemini CLI, Codex, Zed, ChatGPT over HTTP) search, compare and rank professors
using Rate My Professors' public GraphQL endpoint. Companion to `rmp-extension`: same data,
conversational interface instead of in-page injection.

## Where it stands (2026-10-10)

- **1.0.0 built on `feat/universal-package`, not yet published.** Restructured into
  `src/rmp_mcp/` (`client.py`, `matching.py`, `server.py`) with `pyproject.toml`, an
  `rmp-mcp` console script, `--transport stdio|http`, tool annotations, MIT LICENSE,
  CHANGELOG, `server.json` for the MCP registry, and a README with a config block per client.
  Root `server.py` is a compatibility shim.
- Five tools: `search_school` (now returns campuses), `search_professor` and
  `compare_professors` (strict matching ported from the extension, `ambiguous` flag plus
  candidate list instead of a silent first hit), new `get_professor_details` (distribution plus
  five recent reviews), `get_top_professors` (26-letter sweep, 6 concurrent max).
- 40 tests with canned GraphQL responses, 97% coverage, ruff and bandit clean. Live-verified at
  USF, NAU and UCF on 2026-10-09 (the old "USF only" caveat is gone).
- Local Claude Code registration switched to the console script (`.venv/bin/rmp-mcp`).
- Wheel and sdist built in `dist/`.

## Next up

- Kon's go, then: `twine upload dist/*` to PyPI (name `rmp-mcp` is free), publish
  `server.json` to the MCP registry (`mcp-publish`), update the GitHub repo description
  (it still says "lets Claude").
- Push `feat/universal-package`, merge to `main`, tag `v1.0.0`.
- Optional: host the HTTP transport (Render) for zero-install URL clients. Held back on purpose:
  an open proxy to RMP invites abuse and an IP block.

## Open questions

- Whether to add a `get_school_departments` helper so `get_top_professors` filters can be
  discovered instead of guessed.
