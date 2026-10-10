"""Professor-name parsing and strict candidate matching.

Port of the Chrome extension's ``lib/scoring.js`` rules: a candidate must match
the last name exactly; a full first name or a first initial narrows further;
when several candidates survive, the result is flagged ``ambiguous`` instead of
silently picking one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HONORIFIC_RE = re.compile(r"^(dr|prof|professor|mr|mrs|ms|mx)\.?$", re.IGNORECASE)
_SUFFIX_RE = re.compile(r"^(jr|sr|ii|iii|iv|phd|ph\.d|md)\.?$", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedName:
    last_name: str
    first_name: str | None = None
    first_initial: str | None = None


@dataclass(frozen=True)
class MatchResult:
    best: dict | None
    candidates: tuple[dict, ...]
    ambiguous: bool


def _clean_tokens(text: str) -> list[str]:
    tokens = [t for t in re.split(r"\s+", text.strip()) if t]
    tokens = [t for t in tokens if not _HONORIFIC_RE.match(t)]
    while len(tokens) > 1 and _SUFFIX_RE.match(tokens[-1]):
        tokens.pop()
    return tokens


def _is_initial(token: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z]\.?", token))


def parse_name(text: str) -> ParsedName | None:
    """Parse 'Smith', 'J. Smith', 'John Smith', 'Smith, John', 'Dr. John A. Smith'.

    Returns None when no usable last name is present.
    """
    if not text or not text.strip():
        return None
    text = text.strip()

    if "," in text:
        last, _, rest = text.partition(",")
        last_tokens = _clean_tokens(last)
        first_tokens = _clean_tokens(rest)
        if not last_tokens:
            return None
        first = first_tokens[0] if first_tokens else None
        return _build(" ".join(last_tokens), first)

    tokens = _clean_tokens(text)
    if not tokens:
        return None
    if len(tokens) == 1:
        return ParsedName(last_name=tokens[0])
    return _build(" ".join(tokens[1:]), tokens[0])


def _build(last: str, first: str | None) -> ParsedName:
    if not first:
        return ParsedName(last_name=last)
    if _is_initial(first):
        return ParsedName(last_name=last, first_initial=first[0].upper())
    return ParsedName(last_name=last, first_name=first, first_initial=first[0].upper())


def _norm(value: str | None) -> str:
    return re.sub(r"[\s\-'.]", "", (value or "")).lower()


def match_professors(professors: list[dict], parsed: ParsedName) -> MatchResult:
    """Strict match: last name must equal; first name, then initial, narrow the set."""
    by_last = [p for p in professors if _norm(p.get("lastName")) == _norm(parsed.last_name)]
    if not by_last:
        return MatchResult(best=None, candidates=(), ambiguous=False)

    narrowed = by_last
    if parsed.first_name:
        exact = [p for p in by_last if _norm(p.get("firstName")) == _norm(parsed.first_name)]
        if exact:
            narrowed = exact
    if len(narrowed) > 1 and parsed.first_initial:
        by_initial = [
            p for p in narrowed if (p.get("firstName") or "")[:1].upper() == parsed.first_initial
        ]
        if by_initial:
            narrowed = by_initial

    ranked = sorted(narrowed, key=lambda p: p.get("numRatings") or 0, reverse=True)
    exact_first = bool(
        parsed.first_name and _norm(ranked[0].get("firstName")) == _norm(parsed.first_name)
    )
    ambiguous = len(ranked) > 1 and not (exact_first and len(narrowed) == 1)
    return MatchResult(best=ranked[0], candidates=tuple(ranked), ambiguous=ambiguous)
