# Decisions

- 2026-05-08 — Built as a single-file FastMCP server (`server.py`) rather than a package; kept intentionally small alongside the four core tools.
- 2026-05-08 — Use RMP's public GraphQL endpoint directly, no API key or auth required.
- 2026-07-03 — Centralized all RMP network/HTTP/JSON error handling in one `_gql` helper (`RMPError`) instead of per-tool try/except.
