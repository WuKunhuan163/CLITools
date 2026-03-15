"""Simple token estimation for LLM cost tracking.

Provides rough token counts without requiring tiktoken or other heavy deps.
Uses character-based heuristics tuned for mixed CJK/Latin text.
"""

CHARS_PER_TOKEN_CJK = 1.5
CHARS_PER_TOKEN_LATIN = 4.0


def _is_cjk(char: str) -> bool:
    """Check if a character is CJK (Chinese/Japanese/Korean)."""
    cp = ord(char)
    return (
        (0x4E00 <= cp <= 0x9FFF)
        or (0x3400 <= cp <= 0x4DBF)
        or (0xF900 <= cp <= 0xFAFF)
    )


def estimate_tokens(text: str) -> int:
    """Estimate the number of tokens in a text string.

    For mixed CJK/Latin text, counts CJK characters at ~1.5 chars/token
    and Latin characters at ~4 chars/token.

    Returns:
        Estimated token count (minimum 1).
    """
    if not text:
        return 1

    cjk_chars = sum(1 for c in text if _is_cjk(c))
    latin_chars = len(text) - cjk_chars

    cjk_tokens = cjk_chars / CHARS_PER_TOKEN_CJK
    latin_tokens = latin_chars / CHARS_PER_TOKEN_LATIN

    return max(1, round(cjk_tokens + latin_tokens))


def estimate_cost(text: str, price_per_1k: float = 0.001) -> float:
    """Estimate the cost for processing text.

    Args:
        text: Input text.
        price_per_1k: Price per 1000 tokens.

    Returns:
        Estimated cost in the same currency as price_per_1k.
    """
    tokens = estimate_tokens(text)
    return tokens * price_per_1k / 1000


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to approximately max_tokens.

    Uses a conservative estimate to avoid exceeding the limit.
    """
    if max_tokens <= 0:
        return ""

    current = estimate_tokens(text)
    if current <= max_tokens:
        return text

    ratio = max_tokens / current
    cut_point = int(len(text) * ratio * 0.9)
    return text[:cut_point]
