# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.0.0] — 2026-10-10

First packaged release. Works with any MCP client, not only Claude.

### Added
- `get_professor_details`: rating distribution (Awesome to Awful) plus the five most recent reviews for one professor. Accepts the GraphQL id from search results or the numeric id from an RMP profile URL.
- Installable package: `pip install rmp-mcp` / `uvx rmp-mcp`, console script `rmp-mcp`.
- `--transport http --host --port` for Streamable HTTP, so URL-based clients (ChatGPT, claude.ai web, hosted agents) can connect.
- Tool annotations (`readOnlyHint`, `idempotentHint`, `openWorldHint`) so clients that gate on them do not prompt per call.
- `server.json` for the official MCP registry, MIT `LICENSE`, this changelog.
- Test suite with canned GraphQL responses (no live calls).

### Changed
- `search_school` returns up to five campuses, best first, instead of collapsing to one.
- `search_professor` and `compare_professors` use strict matching (exact last name, then first name, then initial) and return every surviving candidate with an `ambiguous` flag. They no longer silently return the first search hit.
- `get_top_professors` sweeps all 26 letters, capped at six concurrent requests.
- `compare_professors` looks names up concurrently.
- Removed the "tested at USF only" caveats; verified at USF, NAU and UCF on 2026-10-09.
- Source moved to `src/rmp_mcp/`; the root `server.py` is a compatibility shim for existing configs.

## [0.1.0] — 2026-07-03

- Single-file FastMCP server with `search_school`, `search_professor`, `compare_professors`, `get_top_professors`.
- Centralized network/HTTP/JSON error handling in `_gql`.
