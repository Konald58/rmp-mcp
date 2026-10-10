"""Canned Rate My Professors GraphQL responses. No test touches the network."""

from __future__ import annotations

from base64 import b64encode

import pytest

from rmp_mcp import client


def tid(n: int) -> str:
    return b64encode(f"Teacher-{n}".encode()).decode()


def sid(n: int) -> str:
    return b64encode(f"School-{n}".encode()).decode()


USF = sid(1262)


def prof(n, first, last, dept, rating=4.0, diff=3.0, wta=80, num=20):
    return {
        "id": tid(n),
        "firstName": first,
        "lastName": last,
        "department": dept,
        "avgRating": rating,
        "avgDifficulty": diff,
        "wouldTakeAgainPercent": wta,
        "numRatings": num,
    }


PROFS = [
    prof(1, "Kenneth", "Mitchell", "Accounting", 4.2, 3.1, 78, 42),
    prof(2, "Kimberly", "Mitchell", "Biology", 3.1, 3.8, 50, 9),
    prof(3, "Joel", "Smith", "Marketing", 5.0, 2.0, 100, 3),
    prof(4, "Tom", "Smith", "Accounting", 3.9, 3.2, 70, 55),
    prof(5, "Jennifer", "Smith-Garvin", "Biology", 4.8, 2.5, 95, 12),
    prof(6, "Alisa", "Lee", "Computer Science", 4.6, 3.0, 90, 30),
    prof(7, "New", "Nobody", "Physics", None, None, 0, 0),
]

SCHOOLS = [
    {
        "id": USF,
        "name": "University of South Florida",
        "city": "Tampa",
        "state": "FL",
        "numRatings": 979,
    },
    {
        "id": sid(4805),
        "name": "University of South Florida",
        "city": "",
        "state": "",
        "numRatings": 49,
    },
    {
        "id": sid(5122),
        "name": "University of South Florida",
        "city": "Lakeland",
        "state": "FL",
        "numRatings": 14,
    },
    {
        "id": sid(2816),
        "name": "South Florida State College",
        "city": "Avon Park",
        "state": "FL",
        "numRatings": 14,
    },
    {
        "id": sid(5393),
        "name": "South Florida Bible College",
        "city": "Deerfield Beach",
        "state": "FL",
        "numRatings": 0,
    },
    {
        "id": sid(5534),
        "name": "DeVry University - South Florida",
        "city": "Miramar",
        "state": "FL",
        "numRatings": 3,
    },
]

DETAILS = {
    **PROFS[0],
    "ratingsDistribution": {"total": 42, "r1": 2, "r2": 3, "r3": 7, "r4": 15, "r5": 15},
    "ratings": {
        "edges": [
            {
                "node": {
                    "class": "ACG2021",
                    "comment": "Clear lectures, fair exams.",
                    "helpfulRating": 5,
                    "clarityRating": 5,
                    "difficultyRating": 3,
                    "wouldTakeAgain": 1,
                    "date": "2026-04-02 14:03:11 +0000 UTC",
                }
            }
        ]
    },
}


class FakeRMP:
    """Stands in for client.gql. Records every call for assertions."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.max_inflight = 0
        self._inflight = 0

    async def __call__(self, query: str, variables: dict) -> dict:
        import asyncio

        self.calls.append((query, variables))
        self._inflight += 1
        self.max_inflight = max(self.max_inflight, self._inflight)
        await asyncio.sleep(0)
        self._inflight -= 1
        if query is client.SCHOOL_SEARCH_QUERY:
            q = variables["query"].lower()
            hits = [s for s in SCHOOLS if q in s["name"].lower()]
            return {"data": {"newSearch": {"schools": {"edges": [{"node": s} for s in hits]}}}}
        if query is client.PROFESSOR_SEARCH_QUERY:
            text = variables["text"].lower()
            hits = [
                p for p in PROFS if text in p["lastName"].lower() or text in p["firstName"].lower()
            ]
            return {"data": {"newSearch": {"teachers": {"edges": [{"node": p} for p in hits]}}}}
        if query is client.PROFESSOR_DETAILS_QUERY:
            node = DETAILS if variables["id"] == DETAILS["id"] else None
            return {"data": {"node": node}}
        raise AssertionError(f"unexpected query: {query[:40]}")


@pytest.fixture
def fake_rmp(monkeypatch):
    fake = FakeRMP()
    monkeypatch.setattr(client, "gql", fake)
    return fake
