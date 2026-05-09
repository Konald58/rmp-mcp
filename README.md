# Rate My Professors MCP Server

An MCP (Model Context Protocol) server that lets Claude search, compare, and rank professors using Rate My Professors data — works at any of the ~1,400 universities on RMP.

> **Testing note:** Verified at University of South Florida (USF Tampa). Other universities should work since they all use the same RMP GraphQL endpoint, but results are unverified.

---

## What it does

Ask Claude things like:
- *"Who's the best professor for Calculus 2 at my university?"*
- *"Compare Smith and Johnson for COP3514"*
- *"What are the top-rated CS professors at USF?"*
- *"Find me a professor for Linear Algebra who's highly rated and not too hard"*

## Tools

| Tool | Description |
|---|---|
| `search_school` | Find a university by name → get its school ID |
| `search_professor` | Look up a professor's rating, difficulty, would-take-again% |
| `compare_professors` | Side-by-side comparison of multiple professors, ranked by rating |
| `get_top_professors` | Top-rated professors at a school, optionally filtered by department |

## Companion project

This MCP server pairs with the **[Professor Ratings for Banner](https://github.com/Konald58/usf-rmp-extension)** Chrome extension, which injects RMP ratings directly into your university's Banner SSB9 course registration system. Same API, two different workflows:

- **Chrome extension** → ratings inline during registration
- **MCP server** → conversational research with Claude before you even open Banner

---

## Installation

### 1. Clone and set up

```bash
git clone https://github.com/Konald58/rmp-mcp.git
cd rmp-mcp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Add to Claude

```bash
claude mcp add-json rmp-mcp '{
  "type": "stdio",
  "command": "/absolute/path/to/rmp-mcp/.venv/bin/python",
  "args": ["/absolute/path/to/rmp-mcp/server.py"]
}'
```

Replace `/absolute/path/to/rmp-mcp` with your actual path (e.g. `/Users/yourname/rmp-mcp`).

### 3. Restart Claude and test

```
Find the school ID for University of South Florida
```

```
Search for professor Smith at school ID U2Nob29sLTEyNjI=
```

---

## Usage example

```
You: Who are the top Computer Science professors at USF?

Claude: [calls search_school("University of South Florida")]
        [calls get_top_professors(school_id=..., department="Computer Science")]

        Here are the top-rated CS professors at USF based on Rate My Professors:

        1. Dr. Jane Doe — 4.8/5 · Difficulty 2.1 · 96% would take again (142 ratings)
        2. Dr. John Smith — 4.6/5 · Difficulty 3.2 · 88% would take again (89 ratings)
        ...
```

---

## How it works

Uses Rate My Professors' public GraphQL endpoint — the same one the official RMP website uses. No API key or authentication required.

---

## Disclaimer

This project is not affiliated with Rate My Professors. Data is sourced from their public GraphQL API and reflects community-submitted ratings. Always use professor ratings as one input among many when choosing courses.

---

## Related

- [Professor Ratings for Banner](https://github.com/Konald58/usf-rmp-extension) — Chrome extension companion
