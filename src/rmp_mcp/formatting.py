"""Shape RMP GraphQL nodes into the dicts the tools return."""

from __future__ import annotations

from rmp_mcp import client


def _tier(rating: float | None) -> str:
    if rating is None:
        return "unrated"
    if rating >= 4.0:
        return "great"
    if rating >= 3.0:
        return "average"
    return "poor"


def _pct(value: float | None) -> int | None:
    """RMP uses -1 and null for 'no data'. Only a real percentage comes through."""
    if value is None or value < 0:
        return None
    return round(value)


def format_professor(node: dict) -> dict:
    rating = node.get("avgRating")
    name = " ".join(part for part in (node.get("firstName"), node.get("lastName")) if part)
    return {
        "professor_id": node["id"],
        "name": name,
        "department": node.get("department") or "Unknown",
        "rating": rating,
        "difficulty": node.get("avgDifficulty"),
        "would_take_again_pct": _pct(node.get("wouldTakeAgainPercent")),
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


def dedupe_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for n in names:
        key = " ".join(n.split()).lower()
        if key and key not in seen:
            seen.add(key)
            out.append(n.strip())
    return out
