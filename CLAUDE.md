# CLAUDE.md — rmp-mcp

## Project

MCP server companion to the **rmp-extension** Chrome extension. Exposes RateMyProfessors data to Claude through a conversational interface, hitting the same RMP GraphQL endpoint the extension uses.

- Repo: https://github.com/Konald58/rmp-mcp
- Stack: Python 3.12, single-file server (`server.py`), `requirements.txt` deps, local `.venv/`.

## Tools

- `search_school` — find a school by name
- `search_professor` — find a professor at a school
- `compare_professors` — compare multiple professors
- `get_top_professors` — top-rated professors at a school

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

Registered with Claude locally as `rmp-mcp`.

## Related

Twin project: the **rmp-extension** Chrome extension (https://github.com/Konald58/rmp-extension) — same RMP GraphQL endpoint, browser-injection interface instead of conversational.
