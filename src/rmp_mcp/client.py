"""Thin async client for Rate My Professors' public GraphQL endpoint.

All network access goes through :func:`gql`, which caps concurrent requests at
``MAX_INFLIGHT`` and turns transport failures into :class:`RMPError` with a
message safe to show to an end user.
"""

from __future__ import annotations

import asyncio
import logging
import re
import weakref
from base64 import b64decode, b64encode

import httpx

logger = logging.getLogger(__name__)

RMP_URL = "https://www.ratemyprofessors.com/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://www.ratemyprofessors.com/",
    "User-Agent": "Mozilla/5.0 (compatible; rmp-mcp)",
}
TIMEOUT_SECONDS = 10
# RMP publishes no rate limit. Six in flight mirrors the companion Chrome
# extension and has never been throttled.
MAX_INFLIGHT = 6


class RMPError(Exception):
    """Raised when the RMP GraphQL endpoint can't be reached or returns something unusable."""


SCHOOL_SEARCH_QUERY = """
query SchoolSearch($query: String!) {
  newSearch {
    schools(query: { text: $query }) {
      edges { node { id name city state numRatings } }
    }
  }
}
"""

PROFESSOR_SEARCH_QUERY = """
query TeacherSearch($text: String!, $schoolID: ID) {
  newSearch {
    teachers(query: { text: $text, schoolID: $schoolID }) {
      edges {
        node {
          id firstName lastName department
          avgRating avgDifficulty wouldTakeAgainPercent numRatings
        }
      }
    }
  }
}
"""

PROFESSOR_DETAILS_QUERY = """
query TeacherDetails($id: ID!) {
  node(id: $id) {
    ... on Teacher {
      id firstName lastName department
      avgRating avgDifficulty wouldTakeAgainPercent numRatings
      ratingsDistribution { total r1 r2 r3 r4 r5 }
      ratings(first: 5) {
        edges {
          node {
            class comment helpfulRating clarityRating difficultyRating
            wouldTakeAgain date
          }
        }
      }
    }
  }
}
"""

# (weakref to the loop, semaphore). A Semaphore keeps a strong reference to
# its loop once contended, so the cache must not hold the loop itself or every
# closed test loop would stay alive.
_sem_cache: tuple[weakref.ref, asyncio.Semaphore] | None = None


def _semaphore() -> asyncio.Semaphore:
    """One semaphore per running event loop, rebuilt when the loop changes."""
    global _sem_cache
    loop = asyncio.get_running_loop()
    if _sem_cache is None or _sem_cache[0]() is not loop:
        _sem_cache = (weakref.ref(loop), asyncio.Semaphore(MAX_INFLIGHT))
    return _sem_cache[1]


async def gql(query: str, variables: dict) -> dict:
    """POST one GraphQL query. Raises RMPError on any transport or decode failure."""
    try:
        async with _semaphore(), httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            resp = await client.post(
                RMP_URL, headers=HEADERS, json={"query": query, "variables": variables}
            )
            resp.raise_for_status()
            payload = resp.json()
    except httpx.TimeoutException as exc:
        logger.warning("RMP request timed out: %s", exc)
        raise RMPError("Rate My Professors took too long to respond. Please try again.") from exc
    except httpx.HTTPStatusError as exc:
        logger.warning("RMP request failed with status %s", exc.response.status_code)
        raise RMPError(
            f"Rate My Professors returned an error (HTTP {exc.response.status_code})."
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("RMP request failed: %s", exc)
        raise RMPError("Couldn't reach Rate My Professors. Please try again later.") from exc
    except ValueError as exc:
        logger.warning("RMP response was not valid JSON: %s", exc)
        raise RMPError("Rate My Professors returned an unexpected response.") from exc
    return _checked(payload)


def _checked(payload: object) -> dict:
    """Reject non-object payloads and GraphQL errors that carry no data at all."""
    if not isinstance(payload, dict):
        logger.warning("RMP response was not a JSON object: %r", type(payload).__name__)
        raise RMPError("Rate My Professors returned an unexpected response.")
    errors = payload.get("errors")
    if errors and not payload.get("data"):
        message = ""
        if isinstance(errors, list) and errors and isinstance(errors[0], dict):
            message = str(errors[0].get("message") or "")[:120]
        logger.warning("RMP GraphQL error: %s", message)
        raise RMPError(
            "Rate My Professors rejected the request"
            + (f": {message}" if message else ".")
            + " Check the school_id (use search_school) and try again."
        )
    return payload


def _edges(data: dict, *path: str) -> list[dict]:
    node: object = data.get("data") or {}
    for key in path:
        if not isinstance(node, dict):
            return []
        node = node.get(key) or {}
    if not isinstance(node, dict):
        return []
    return [e["node"] for e in node.get("edges", []) if isinstance(e, dict) and "node" in e]


async def search_schools(text: str) -> list[dict]:
    data = await gql(SCHOOL_SEARCH_QUERY, {"query": text})
    return _edges(data, "newSearch", "schools")


async def search_teachers(text: str, school_id: str) -> list[dict]:
    data = await gql(PROFESSOR_SEARCH_QUERY, {"text": text, "schoolID": school_id})
    return _edges(data, "newSearch", "teachers")


async def teacher_details(graphql_id: str) -> dict | None:
    data = await gql(PROFESSOR_DETAILS_QUERY, {"id": graphql_id})
    node = (data.get("data") or {}).get("node")
    return node if isinstance(node, dict) and node.get("id") else None


def _is_ascii_digits(value: str) -> bool:
    return value.isascii() and value.isdigit()


def numeric_id(graphql_id: str) -> str | None:
    """'VGVhY2hlci0xMjM=' -> '123'. None if the id is not RMP-shaped."""
    try:
        tail = b64decode(graphql_id, validate=True).decode().split("-").pop()
    except Exception:  # noqa: BLE001 - any decode failure means "not an RMP id"
        return None
    return tail if _is_ascii_digits(tail) else None


def _graphql_id(kind: str, value: str, url_segment: str) -> str:
    """Accept a GraphQL id, a bare numeric id, or an RMP URL; return the GraphQL id."""
    value = value.strip()
    m = re.search(rf"/{url_segment}/(\d+)", value)
    if m:
        value = m.group(1)
    if _is_ascii_digits(value):
        return b64encode(f"{kind}-{value}".encode()).decode()
    return value


def teacher_graphql_id(value: str) -> str:
    return _graphql_id("Teacher", value, "professor")


def school_graphql_id(value: str) -> str:
    return _graphql_id("School", value, "school")


def professor_url(graphql_id: str) -> str:
    n = numeric_id(graphql_id)
    return (
        f"https://www.ratemyprofessors.com/professor/{n}"
        if n
        else "https://www.ratemyprofessors.com"
    )


def school_url(graphql_id: str) -> str:
    n = numeric_id(graphql_id)
    return (
        f"https://www.ratemyprofessors.com/school/{n}" if n else "https://www.ratemyprofessors.com"
    )
