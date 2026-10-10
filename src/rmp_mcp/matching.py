"""Professor-name parsing and strict candidate matching.

Same rules as the Chrome extension's ``lib/scoring.js``: the last name must
match; a first initial, when given, must match too; an exact first name wins
outright. When several candidates survive, the result is ``ambiguous`` rather
than a silent pick, and a first name that matched nothing is reported.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_HONORIFIC_RE = re.compile(r"^(dr|prof|professor|mr|mrs|ms|mx)\.?$", re.IGNORECASE)
_SUFFIX_RE = re.compile(r"^(jr|sr|ii|iii|iv|phd|ph\.d|md|esq)\.?,?$", re.IGNORECASE)
_PARTICLES = {"da", "de", "del", "della", "der", "di", "du", "la", "le", "van", "von", "st", "st."}


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
    first_name_mismatch: bool = False


def _fold(value: str | None) -> str:
    """Case-, accent- and punctuation-insensitive comparison key."""
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("’", "'").replace("‘", "'")
    return re.sub(r"[\s\-'.,]", "", text).lower()


def _tokens(text: str) -> list[str]:
    tokens = [t.strip(",") for t in re.split(r"\s+", text.strip()) if t.strip(",")]
    tokens = [t for t in tokens if not _HONORIFIC_RE.match(t)]
    while len(tokens) > 1 and _SUFFIX_RE.match(tokens[-1]):
        tokens.pop()
    return tokens


def _is_initial(token: str) -> bool:
    return bool(re.fullmatch(r"[^\W\d_]\.?", token))


def _strip_middle(tokens: list[str]) -> list[str]:
    """Drop middle initials: 'John A. Smith' -> ['John', 'Smith']. Keep particles."""
    if len(tokens) <= 2:
        return tokens
    return [tokens[0]] + [t for t in tokens[1:-1] if not _is_initial(t)] + [tokens[-1]]


def parse_name(text: str) -> ParsedName | None:
    """Parse 'Smith', 'J. Smith', 'John Smith', 'Smith, John', 'Dr. John A. Smith, PhD'.

    Returns None when no usable last name is present.
    """
    if not text or not text.strip():
        return None
    parts = [p.strip() for p in text.split(",")]
    parts = [p for p in parts if p and not _SUFFIX_RE.match(p)]
    if not parts:
        return None

    if len(parts) >= 2:  # "Last, First [Middle]"
        last_tokens = _tokens(parts[0])
        first_tokens = _tokens(parts[1])
        if not last_tokens:
            return None
        return _build(" ".join(last_tokens), first_tokens[0] if first_tokens else None)

    tokens = _strip_middle(_tokens(parts[0]))
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


def search_text(parsed: ParsedName) -> str:
    """What to send to RMP search: the last word of the last name, which is what RMP indexes."""
    return parsed.last_name.split()[-1]


def _last_name_matches(candidate: dict, parsed: ParsedName) -> bool:
    cand = _fold(candidate.get("lastName"))
    if not cand:
        return False
    if cand == _fold(parsed.last_name):
        return True
    # "John Michael Smith" parses with last name "Michael Smith"; accept the final token.
    words = parsed.last_name.split()
    return len(words) > 1 and words[-2].lower() not in _PARTICLES and cand == _fold(words[-1])


def match_professors(professors: list[dict], parsed: ParsedName) -> MatchResult:
    """Strict match. Never returns a candidate whose first initial contradicts the query."""
    by_last = [p for p in professors if _last_name_matches(p, parsed)]
    if not by_last:
        return MatchResult(best=None, candidates=(), ambiguous=False)

    mismatch = False
    narrowed = by_last
    if parsed.first_name:
        exact = [p for p in by_last if _fold(p.get("firstName")) == _fold(parsed.first_name)]
        if exact:
            narrowed = exact
        else:
            mismatch = True
    if narrowed is by_last and parsed.first_initial:
        narrowed = [
            p for p in by_last if _fold(p.get("firstName"))[:1] == parsed.first_initial.lower()
        ]
        if not narrowed:
            return MatchResult(best=None, candidates=(), ambiguous=False, first_name_mismatch=True)

    ranked = sorted(narrowed, key=lambda p: p.get("numRatings") or 0, reverse=True)
    return MatchResult(
        best=ranked[0],
        candidates=tuple(ranked),
        ambiguous=len(ranked) > 1 or mismatch,
        first_name_mismatch=mismatch,
    )
