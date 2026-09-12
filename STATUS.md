---
status: dormant
---

# rmp-mcp

## What it is

An MCP (Model Context Protocol) server that lets Claude search, compare, and rank professors using Rate My Professors data, via RMP's public GraphQL endpoint. Companion project to the `rmp-extension` Chrome extension — same data source, conversational interface instead of in-page injection.

## Where it stands (2026-09-12)

- Public repo, 3 commits, last commit 2026-07-03 (`fix: handle network/HTTP/JSON errors in _gql cleanly`). No activity since.
- Functional: 4 tools (`search_school`, `search_professor`, `compare_professors`, `get_top_professors`) in a single `server.py`, backed by `httpx` + `fastmcp`.
- Verified working at University of South Florida (USF Tampa) only; other schools are expected to work (same RMP endpoint) but are unverified, per the README's own testing note.
- No automated tests, no LICENSE file.

## Next up

- Extend verification to schools beyond USF.
- Add a basic test suite (per repo conventions, this predates the standard project shape and has none yet).
- Add a LICENSE file.
- Align release/documentation with the `rmp-extension` companion project when that project's own launch activity resumes.

## Open questions

- Should this stay a single-file server as tool count grows, or split once it's no longer trivially readable?
- Is there interest in submitting this to a public MCP server registry/directory?
