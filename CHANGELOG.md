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
- `school_id` and `professor_id` accept a GraphQL id, a bare numeric id, or the RMP profile URL.
- Input bounds at the tool boundary (name lengths, `min_ratings` 0 to 10,000, at most 10 names per comparison, duplicates removed).
- Review comments are capped at 500 characters and flagged `untrusted_content`; the server instructions tell clients that names and review text are data, not instructions.
- `compare_professors` and `get_top_professors` report partial failures instead of aborting the whole call.
- HTTP transport logs a warning when bound to a non-loopback host.

### Changed
- `search_school` returns up to five campuses, best first, instead of collapsing to one.
- `search_professor` and `compare_professors` use strict matching: the last name must match, a first initial must match, an exact first name wins. Every surviving candidate is returned with an `ambiguous` flag, a first name that matched nobody is reported, and a wrong initial is "not found" rather than a guess. Middle initials, suffixes (`Jr.`, `PhD`), honorifics, hyphens, curly apostrophes and accents are handled.
- Any error reaching a client is a `ToolError` with a user-safe message; RMP's HTTP 200 + `errors` responses (typically a bad `school_id`) are reported as such instead of "not found".
- `get_top_professors` sweeps all 26 letters, capped at six concurrent requests.
- `compare_professors` looks names up concurrently.
- Removed the "tested at USF only" caveats; verified at USF, NAU and UCF on 2026-10-09.
- Source moved to `src/rmp_mcp/`; the root `server.py` is a compatibility shim for existing configs.

## [0.1.0] — 2026-07-03

- Single-file FastMCP server with `search_school`, `search_professor`, `compare_professors`, `get_top_professors`.
- Centralized network/HTTP/JSON error handling in `_gql`.
