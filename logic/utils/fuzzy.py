"""Fuzzy command matching using stdlib difflib.

Provides a unified interface for suggesting close matches when a user
types an unrecognized command or option.
"""
import difflib
from typing import List, Optional, Tuple


def suggest_commands(
    input_cmd: str,
    candidates: List[str],
    n: int = 3,
    cutoff: float = 0.5,
) -> List[str]:
    """Return up to *n* candidates that closely match *input_cmd*.

    Uses ``difflib.get_close_matches`` internally.  The *cutoff* parameter
    controls how similar a candidate must be (0.0 -- 1.0; higher is stricter).
    """
    return difflib.get_close_matches(input_cmd, candidates, n=n, cutoff=cutoff)


def suggest_with_scores(
    input_cmd: str,
    candidates: List[str],
    n: int = 3,
    cutoff: float = 0.4,
) -> List[Tuple[str, float]]:
    """Return up to *n* (candidate, similarity_ratio) pairs sorted by score.

    Useful when the caller wants to display the confidence level.
    """
    scored: List[Tuple[str, float]] = []
    for c in candidates:
        ratio = difflib.SequenceMatcher(None, input_cmd.lower(), c.lower()).ratio()
        if ratio >= cutoff:
            scored.append((c, ratio))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:n]


def format_suggestion(
    input_cmd: str,
    candidates: List[str],
    n: int = 3,
    cutoff: float = 0.5,
    prefix: str = "  Did you mean: ",
) -> Optional[str]:
    """Return a formatted suggestion string, or None if no match found."""
    matches = suggest_commands(input_cmd, candidates, n=n, cutoff=cutoff)
    if not matches:
        return None
    joined = ", ".join(matches)
    return f"{prefix}{joined}"
