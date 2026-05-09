#!/usr/bin/env python3
"""
Rate My Professors MCP Server

Lets Claude search, compare, and rank professors using Rate My Professors data.
Works at any university supported by RMP (~1,400 institutions).

Tested at: University of South Florida (USF Tampa)
Other schools should work but results are unverified.

Add to Claude Desktop via terminal:
  claude mcp add-json rmp-mcp '{
    "type": "stdio",
    "command": "/Users/<you>/rmp-mcp/.venv/bin/python",
    "args": ["/Users/<you>/rmp-mcp/server.py"]
  }'
"""
import logging
from base64 import b64decode
from typing import Optional

import httpx
from fastmcp import FastMCP

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

mcp = FastMCP("Rate My Professors")

RMP_URL = "https://www.ratemyprofessors.com/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://www.ratemyprofessors.com/",
    "User-Agent": "Mozilla/5.0",
}

# ---------------------------------------------------------------------------
# GraphQL queries
# ---------------------------------------------------------------------------

_SCHOOL_SEARCH_QUERY = """
query SchoolSearch($query: String!) {
  newSearch {
    schools(query: { text: $query }) {
      edges {
        node {
          id
          name
          city
          state
          numRatings
        }
      }
    }
  }
}
"""

_PROFESSOR_SEARCH_QUERY = """
query TeacherSearch($text: String!, $schoolID: ID) {
  newSearch {
    teachers(query: { text: $text, schoolID: $schoolID }) {
      edges {
        node {
          id
          firstName
          lastName
          department
          avgRating
          avgDifficulty
          wouldTakeAgainPercent
          numRatings
        }
      }
    }
  }
}
"""

_PROFESSOR_RATINGS_QUERY = """
query TeacherRatingsPageQuery($id: ID!) {
  node(id: $id) {
    ... on Teacher {
      id
      firstName
      lastName
      department
      avgRating
      avgDifficulty
      wouldTakeAgainPercent
      numRatings
      ratingsDistribution {
        total
        r1
        r2
        r3
        r4
        r5
      }
      ratings(first: 5) {
        edges {
          node {
            class
            comment
            helpfulRating
            clarityRating
            difficultyRating
            date
          }
        }
      }
    }
  }
}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _professor_url(graphql_id: str) -> str:
    try:
        numeric = b64decode(graphql_id).decode().split("-").pop()
        if numeric.isdigit():
            return f"https://www.ratemyprofessors.com/professor/{numeric}"
    except Exception:
        pass
    return "https://www.ratemyprofessors.com"


def _tier(rating: float) -> str:
    if rating >= 4.0:
        return "great"
    if rating >= 3.0:
        return "average"
    return "poor"


async def _gql(query: str, variables: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            RMP_URL,
            headers=HEADERS,
            json={"query": query, "variables": variables},
        )
        resp.raise_for_status()
        return resp.json()


async def _resolve_school(school_name: str) -> Optional[dict]:
    """Return the best-matching school node for a human-readable name."""
    data = await _gql(_SCHOOL_SEARCH_QUERY, {"query": school_name})
    edges = data.get("data", {}).get("newSearch", {}).get("schools", {}).get("edges", [])
    if not edges:
        return None
    # Return the school with the most ratings as the canonical match
    return max((e["node"] for e in edges), key=lambda n: n.get("numRatings", 0))


async def _search_professors(name: str, school_graphql_id: str) -> list[dict]:
    data = await _gql(_PROFESSOR_SEARCH_QUERY, {"text": name, "schoolID": school_graphql_id})
    edges = data.get("data", {}).get("newSearch", {}).get("teachers", {}).get("edges", [])
    return [e["node"] for e in edges]


def _format_professor(node: dict) -> dict:
    return {
        "name": f"{node['firstName']} {node['lastName']}",
        "department": node.get("department", "Unknown"),
        "rating": node.get("avgRating"),
        "difficulty": node.get("avgDifficulty"),
        "would_take_again_pct": round(node.get("wouldTakeAgainPercent") or 0),
        "num_ratings": node.get("numRatings", 0),
        "tier": _tier(node.get("avgRating") or 0),
        "rmp_url": _professor_url(node["id"]),
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def search_school(university_name: str) -> dict:
    """
    Find a university on Rate My Professors by name.
    Returns the school ID needed for professor searches, plus basic info.

    Tested at USF — other schools should work but are unverified.
    """
    school = await _resolve_school(university_name)
    if not school:
        return {"found": False, "query": university_name}
    return {
        "found": True,
        "name": school["name"],
        "city": school.get("city"),
        "state": school.get("state"),
        "school_id": school["id"],
        "num_ratings": school.get("numRatings", 0),
        "note": "Pass school_id into other tools to scope results to this university.",
    }


@mcp.tool()
async def search_professor(
    professor_name: str,
    school_id: str,
) -> dict:
    """
    Search for a professor at a specific university by name.
    Returns ratings, difficulty, would-take-again%, and a direct RMP link.

    Get school_id from search_school first.
    Tested at USF — other schools should work but are unverified.
    """
    professors = await _search_professors(professor_name, school_id)
    if not professors:
        return {
            "found": False,
            "query": professor_name,
            "tip": "Try last name only, or check spelling.",
        }

    # Best match: exact last name first, then first result
    query_last = professor_name.strip().split()[-1].lower()
    match = next(
        (p for p in professors if p["lastName"].lower() == query_last),
        professors[0],
    )

    result = _format_professor(match)
    if len(professors) > 1:
        result["other_matches"] = [
            f"{p['firstName']} {p['lastName']} ({p.get('department', '?')})"
            for p in professors[1:4]
        ]
    return {"found": True, **result}


@mcp.tool()
async def compare_professors(
    professor_names: list[str],
    school_id: str,
) -> dict:
    """
    Compare multiple professors at the same university side by side.
    Ranked by rating (highest first).

    Get school_id from search_school first.
    Tested at USF — other schools should work but are unverified.
    """
    results = []
    not_found = []

    for name in professor_names:
        professors = await _search_professors(name, school_id)
        if not professors:
            not_found.append(name)
            continue
        query_last = name.strip().split()[-1].lower()
        match = next(
            (p for p in professors if p["lastName"].lower() == query_last),
            professors[0],
        )
        results.append(_format_professor(match))

    results.sort(key=lambda p: p.get("rating") or 0, reverse=True)

    return {
        "ranked": results,
        "not_found": not_found,
        "summary": (
            f"Best pick: {results[0]['name']} ({results[0]['rating']}/5, "
            f"{results[0]['would_take_again_pct']}% would take again)"
            if results
            else "No results found."
        ),
    }


@mcp.tool()
async def get_top_professors(
    school_id: str,
    department: Optional[str] = None,
    min_ratings: int = 10,
) -> dict:
    """
    Find highly-rated professors at a university, optionally filtered by department.
    Runs multiple broad searches (common name fragments) to collect a wide sample,
    then filters by department and ranks by rating.

    department examples: "Computer Science", "Mathematics", "Biology"
    min_ratings: ignore professors with fewer reviews than this (default 10).
    Tested at USF — other schools should work but are unverified.
    """
    import asyncio as _asyncio

    # RMP returns ~20 results per query — sweep common name fragments for breadth.
    # This covers a sample, not every professor at the school.
    broad_terms = ["a", "b", "c", "d", "e", "h", "j", "k", "l", "m",
                   "n", "o", "p", "r", "s", "t", "w"]
    tasks = [_search_professors(term, school_id) for term in broad_terms]
    results_nested = await _asyncio.gather(*tasks)

    seen_ids: set[str] = set()
    all_professors: list[dict] = []
    for batch in results_nested:
        for p in batch:
            if p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                all_professors.append(p)

    qualified = [
        p for p in all_professors
        if (p.get("numRatings") or 0) >= min_ratings and p.get("avgRating")
    ]

    if department:
        dept_lower = department.lower()
        qualified = [
            p for p in qualified
            if dept_lower in (p.get("department") or "").lower()
        ]

    qualified.sort(key=lambda p: p.get("avgRating") or 0, reverse=True)
    top = [_format_professor(p) for p in qualified[:10]]

    note = (
        "Results cover a sample of professors found via RMP search — not a complete department roster. "
        "Tested at USF; other schools should work but are unverified."
    )
    if department and not top:
        return {
            "department_filter": department,
            "min_ratings_filter": min_ratings,
            "count": 0,
            "professors": [],
            "note": f"No professors found in '{department}' with ≥{min_ratings} ratings in this sample. "
                    "Try a broader department name (e.g. 'Computer' instead of 'Computer Science'), "
                    "or lower min_ratings.",
        }

    return {
        "department_filter": department,
        "min_ratings_filter": min_ratings,
        "count": len(top),
        "professors": top,
        "note": note,
    }


if __name__ == "__main__":
    mcp.run()
