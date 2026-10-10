# Decisions

- 2026-05-08 — Built as a single-file FastMCP server (`server.py`) rather than a package; kept intentionally small alongside the four core tools.
- 2026-05-08 — Use RMP's public GraphQL endpoint directly, no API key or auth required.
- 2026-07-03 — Centralized all RMP network/HTTP/JSON error handling in one `_gql` helper (`RMPError`) instead of per-tool try/except.
- 2026-10-10 — Restructured into a `src/rmp_mcp/` package with a console script instead of the single-file server, so it installs with `uvx rmp-mcp` from any MCP client. Root `server.py` kept as a shim for pre-1.0 configs.
- 2026-10-10 — Professor matching is strict (exact last name, then first name, then initial) and returns every surviving candidate with an `ambiguous` flag. Silently returning the first search hit was the same wrong-professor bug the extension fixed in May.
- 2026-10-10 — Concurrent RMP requests capped at 6 (one semaphore per event loop), matching the extension. `get_top_professors` sweeps all 26 letters.
- 2026-10-10 — HTTP transport is a CLI flag, not a hosted service. Hosting is deferred: no auth on the server and an open proxy to RMP invites abuse.
