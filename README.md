# Rate My Professors MCP Server

An [MCP](https://modelcontextprotocol.io) server that lets any AI client search, compare and rank professors with [Rate My Professors](https://www.ratemyprofessors.com) data, at any of the ~1,400 universities RMP covers. Works with Claude, Cursor, VS Code, Windsurf, Gemini CLI, Codex, Zed, ChatGPT and anything else that speaks MCP over stdio or Streamable HTTP.

No API key. No account. One command to install.

## What you can ask

- "Who's the best professor for Calculus 2 at my university?"
- "Compare Smith and Johnson for COP3514"
- "What are the top-rated CS professors at UCF?"
- "Show me the rating distribution and recent reviews for Kenneth Mitchell"

## Tools

| Tool | What it does |
|---|---|
| `search_school` | Find a university by name. Returns up to five campuses, best first, with the `school_id` the other tools need |
| `search_professor` | Look up one professor by "Smith", "J. Smith", "John Smith" or "Smith, John". Strict last-name match; flags `ambiguous` and lists every candidate when several share the name |
| `get_professor_details` | Rating distribution (Awesome to Awful) plus the five most recent reviews |
| `compare_professors` | Several professors at one school, ranked by rating, looked up concurrently |
| `get_top_professors` | Highest-rated professors at a school, optionally filtered by department, from a broad A-to-Z search sample |

Every tool is read-only and idempotent, and says so in its annotations, so clients that gate on annotations do not prompt per call.

## Install

Requires Python 3.10+. The quickest path is [uv](https://docs.astral.sh/uv/), which runs the server in an isolated environment:

```bash
uvx rmp-mcp
```

Or with pip:

```bash
pip install rmp-mcp
rmp-mcp
```

Until the PyPI release lands you can run straight from GitHub:

```bash
uvx --from git+https://github.com/Konald58/rmp-mcp rmp-mcp
```

Options:

```
rmp-mcp [--transport stdio|http] [--host 127.0.0.1] [--port 8000] [--version]
```

`stdio` (default) is what local desktop and CLI clients use. `http` serves Streamable HTTP at `http://HOST:PORT/mcp` for URL-based clients.

## Add it to your client

All stdio configs are the same shape: command `uvx`, args `["rmp-mcp"]`. If you installed with pip instead, use command `rmp-mcp` with no args.

### Claude Desktop

`claude_desktop_config.json` (Settings > Developer > Edit Config):

```json
{
  "mcpServers": {
    "rmp": { "command": "uvx", "args": ["rmp-mcp"] }
  }
}
```

### Claude Code

```bash
claude mcp add rmp -- uvx rmp-mcp
```

### Cursor

`.cursor/mcp.json` in your project, or `~/.cursor/mcp.json` globally:

```json
{
  "mcpServers": {
    "rmp": { "command": "uvx", "args": ["rmp-mcp"] }
  }
}
```

### VS Code (GitHub Copilot)

`.vscode/mcp.json`:

```json
{
  "servers": {
    "rmp": { "type": "stdio", "command": "uvx", "args": ["rmp-mcp"] }
  }
}
```

### Windsurf

`~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "rmp": { "command": "uvx", "args": ["rmp-mcp"] }
  }
}
```

### Gemini CLI

`~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "rmp": { "command": "uvx", "args": ["rmp-mcp"] }
  }
}
```

### Codex CLI

`~/.codex/config.toml`:

```toml
[mcp_servers.rmp]
command = "uvx"
args = ["rmp-mcp"]
```

### Zed

`settings.json`:

```json
{
  "context_servers": {
    "rmp": { "source": "custom", "command": "uvx", "args": ["rmp-mcp"] }
  }
}
```

### ChatGPT, claude.ai on the web, and other URL-based clients

These need a reachable HTTP endpoint. Run the server with the HTTP transport, expose it (a tunnel such as `cloudflared` or `ngrok` is enough for personal use), and add the URL as a custom connector:

```bash
rmp-mcp --transport http --host 0.0.0.0 --port 8000
# endpoint: http://<your-host>:8000/mcp
```

The server has no authentication of its own. Put it behind your tunnel's access controls rather than on the open internet.

## Try it

```
Find the school ID for University of South Florida
```

```
Compare Joel Smith and Tom Smith at that school
```

```
Show me details for professor 3050642
```

## How it works

The server talks to the same public GraphQL endpoint the RMP website uses, with at most six requests in flight at once. Name matching is strict: the last name must match exactly, a first name or initial narrows the set, and if several professors still match you get all of them plus an `ambiguous` flag instead of a silent guess. This is the same rule set as the companion Chrome extension.

## Companion project

[Professor Ratings for Course Search](https://github.com/Konald58/rmp-extension) is a Chrome extension that injects the same ratings directly into Banner, PeopleSoft and UO DuckWeb registration pages. Same data, two workflows:

- Chrome extension: ratings inline while you register
- MCP server: conversational research in whichever AI client you already use

## Development

```bash
git clone https://github.com/Konald58/rmp-mcp.git
cd rmp-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest            # canned responses, no network
ruff check src tests
bandit -r src
```

Layout: `src/rmp_mcp/client.py` (GraphQL client, concurrency cap, error mapping), `matching.py` (name parsing and strict matching), `server.py` (tools and CLI). The root `server.py` is a shim so configs from before 1.0 keep working.

## Disclaimer

Not affiliated with Rate My Professors. Data comes from their public GraphQL API and reflects community-submitted ratings. Use it as one input among many when choosing courses.

## License

[MIT](LICENSE)
