"""Rate My Professors MCP server: tools and command-line entry point.

Works with any MCP client (Claude, Cursor, VS Code, Windsurf, Gemini CLI,
Codex, Zed, ChatGPT via HTTP, ...). Transport is stdio by default; pass
``--transport http`` for Streamable HTTP.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import string

from fastmcp import FastMCP

from rmp_mcp import __version__, client
from rmp_mcp.client import RMPError
from rmp_mcp.matching import match_professors, parse_name

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

INSTRUCTIONS = (
    "Look up Rate My Professors data for any university. Start with search_school to get a "
    "school_id, then search_professor / compare_professors / get_top_professors with that id. "
    "get_professor_details returns the rating distribution and recent reviews for one professor. "
    "Ratings are community-submitted: present them as one input, never a verdict."
)

READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}

mcp = FastMCP("Rate My Professors", instructions=INSTRUCTIONS, version=__version__)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _tier(rating: float | None) -> str:
    if rating is None:
        return "unrated"
    if rating >= 4.0:
        return "great"
    if rating >= 3.0:
        return "average"
    return "poor"


def format_professor(node: dict) -> dict:
    rating = node.get("avgRating")
    return {
        "professor_id": node["id"],
        "name": f"{node.get('firstName', '')} {node.get('lastName', '')}".strip(),
        "department": node.get("department") or "Unknown",
        "rating": rating,
        "difficulty": node.get("avgDifficulty"),
        "would_take_again_pct": round(node.get("wouldTakeAgainPercent") or 0),
        "num_ratings": node.get("numRatings") or 0,
        "tier": _tier(rating),
        "rmp_url": client.professor_url(node["id"]),
    }


def format_school(node: dict) -> dict:
    return {
        "school_id": node["id"],
        "name": node.get("name"),
        "city": node.get("city") or None,
        "state": node.get("state") or None,
        "num_ratings": node.get("numRatings") or 0,
        "rmp_url": client.school_url(node["id"]),
    }


async def _lookup(name: str, school_id: str) -> dict:
    """Shared by search_professor and compare_professors."""
    parsed = parse_name(name)
    if parsed is None:
        return {"found": False, "query": name, "tip": "Give at least a last name."}
    professors = await client.search_teachers(parsed.last_name, school_id)
    match = match_professors(professors, parsed)
    if match.best is None:
        return {
            "found": False,
            "query": name,
            "tip": "No professor with that last name at this school. Check the spelling, "
            "or confirm the school_id with search_school.",
            "similar": [format_professor(p)["name"] for p in professors[:5]],
        }
    result = {
        "found": True,
        "query": name,
        "professor": format_professor(match.best),
        "ambiguous": match.ambiguous,
    }
    if len(match.candidates) > 1:
        result["candidates"] = [format_professor(p) for p in match.candidates]
    if match.ambiguous:
        result["note"] = (
            "Several professors match this name. The best guess is the one with the most "
            "ratings; add a first name or pick from candidates to be sure."
        )
    return result


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


async def search_school(university_name: str) -> dict:
    """Find a university on Rate My Professors by name.

    Returns up to five matching campuses, best (most-rated) first, each with the
    school_id that every other tool needs.
    """
    schools = await client.search_schools(university_name)
    if not schools:
        return {"found": False, "query": university_name, "schools": []}
    ranked = sorted(schools, key=lambda s: s.get("numRatings") or 0, reverse=True)[:5]
    return {
        "found": True,
        "query": university_name,
        "best": format_school(ranked[0]),
        "schools": [format_school(s) for s in ranked],
        "note": "Pass school_id into search_professor, compare_professors or get_top_professors.",
    }


async def search_professor(professor_name: str, school_id: str) -> dict:
    """Look up one professor at a university by name.

    Accepts "Smith", "J. Smith", "John Smith" or "Smith, John". Matching is
    strict on last name; a first name or initial narrows further. When several
    professors still match, `ambiguous` is true and `candidates` lists them all.
    Get school_id from search_school.
    """
    return await _lookup(professor_name, school_id)


async def get_professor_details(professor_id: str) -> dict:
    """Rating distribution and the five most recent reviews for one professor.

    professor_id is the value returned by search_professor, or the number at
    the end of an RMP profile URL (ratemyprofessors.com/professor/123456).
    """
    node = await client.teacher_details(client.teacher_graphql_id(professor_id))
    if node is None:
        return {"found": False, "professor_id": professor_id, "tip": "Unknown professor id."}
    dist = node.get("ratingsDistribution") or {}
    reviews = []
    for edge in (node.get("ratings") or {}).get("edges", []):
        r = edge.get("node") or {}
        reviews.append(
            {
                "class": r.get("class"),
                "date": (r.get("date") or "")[:10] or None,
                "quality": r.get("clarityRating"),
                "difficulty": r.get("difficultyRating"),
                "would_take_again": r.get("wouldTakeAgain"),
                "comment": r.get("comment"),
            }
        )
    return {
        "found": True,
        "professor": format_professor(node),
        "distribution": {
            "total": dist.get("total") or 0,
            "awesome_5": dist.get("r5") or 0,
            "great_4": dist.get("r4") or 0,
            "good_3": dist.get("r3") or 0,
            "ok_2": dist.get("r2") or 0,
            "awful_1": dist.get("r1") or 0,
        },
        "recent_reviews": reviews,
    }


async def compare_professors(professor_names: list[str], school_id: str) -> dict:
    """Compare several professors at one university, ranked by rating.

    Each name is matched the same way as search_professor; ambiguous matches
    are flagged rather than guessed silently. Get school_id from search_school.
    """
    lookups = await asyncio.gather(*(_lookup(n, school_id) for n in professor_names))
    ranked = [r for r in lookups if r.get("found")]
    ranked.sort(key=lambda r: r["professor"].get("rating") or 0, reverse=True)
    not_found = [r["query"] for r in lookups if not r.get("found")]
    summary = "No results found."
    if ranked:
        top = ranked[0]["professor"]
        summary = (
            f"Best pick: {top['name']} ({top['rating']}/5, "
            f"{top['would_take_again_pct']}% would take again, {top['num_ratings']} ratings)"
        )
        if any(r["ambiguous"] for r in ranked):
            summary += ". At least one match is ambiguous; check candidates before deciding."
    return {
        "ranked": [
            {"professor": r["professor"], "ambiguous": r["ambiguous"], "query": r["query"]}
            for r in ranked
        ],
        "not_found": not_found,
        "summary": summary,
    }


async def get_top_professors(
    school_id: str, department: str | None = None, min_ratings: int = 10
) -> dict:
    """Highly rated professors at a university, optionally filtered by department.

    Sweeps RMP search with every letter of the alphabet to collect a broad
    sample, then filters by department substring and ranks by rating. The
    sample is wide but not a complete roster. Get school_id from search_school.
    """
    batches = await asyncio.gather(
        *(client.search_teachers(letter, school_id) for letter in string.ascii_lowercase)
    )
    seen: set[str] = set()
    pool: list[dict] = []
    for batch in batches:
        for p in batch:
            if p["id"] not in seen:
                seen.add(p["id"])
                pool.append(p)

    qualified = [
        p for p in pool if (p.get("numRatings") or 0) >= min_ratings and p.get("avgRating")
    ]
    if department:
        needle = department.lower()
        qualified = [p for p in qualified if needle in (p.get("department") or "").lower()]
    qualified.sort(key=lambda p: p.get("avgRating") or 0, reverse=True)

    result = {
        "department_filter": department,
        "min_ratings_filter": min_ratings,
        "sampled": len(pool),
        "count": min(len(qualified), 10),
        "professors": [format_professor(p) for p in qualified[:10]],
    }
    if not result["professors"]:
        result["note"] = (
            "Nothing matched in this sample. Try a broader department word "
            "(e.g. 'Computer' instead of 'Computer Science') or a lower min_ratings."
        )
    else:
        result["note"] = "Ranked from a broad search sample, not a complete department roster."
    return result


TOOLS = (
    search_school,
    search_professor,
    get_professor_details,
    compare_professors,
    get_top_professors,
)
for _fn in TOOLS:
    mcp.tool(_fn, annotations=READ_ONLY)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rmp-mcp", description="Rate My Professors MCP server (stdio or Streamable HTTP)."
    )
    parser.add_argument("--version", action="version", version=f"rmp-mcp {__version__}")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio for local clients (default); http for URL-based clients.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host (default 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (default 8000).")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()


__all__ = ["RMPError", "main", "mcp", *[t.__name__ for t in TOOLS]]
