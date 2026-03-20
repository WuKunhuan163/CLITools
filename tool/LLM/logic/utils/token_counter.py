"""Token counting for LLM cost tracking.

Uses tiktoken (OpenAI's tokenizer) when available for accurate counts.
Falls back to character-based heuristics for mixed CJK/Latin text.
"""

import functools
from typing import Optional

CHARS_PER_TOKEN_CJK = 1.5
CHARS_PER_TOKEN_LATIN = 4.0

_tiktoken_enc = None
_tiktoken_loaded = False


def _get_tiktoken_encoder():
    """Lazy-load tiktoken cl100k_base encoder (used by GPT-4, compatible baseline)."""
    global _tiktoken_enc, _tiktoken_loaded
    if _tiktoken_loaded:
        return _tiktoken_enc
    _tiktoken_loaded = True
    try:
        import tiktoken
        _tiktoken_enc = tiktoken.get_encoding("cl100k_base")
    except Exception:
        _tiktoken_enc = None
    return _tiktoken_enc


def _is_cjk(char: str) -> bool:
    cp = ord(char)
    return (
        (0x4E00 <= cp <= 0x9FFF)
        or (0x3400 <= cp <= 0x4DBF)
        or (0xF900 <= cp <= 0xFAFF)
    )


def _estimate_heuristic(text: str) -> int:
    """Heuristic token estimate for mixed CJK/Latin text."""
    if not text:
        return 1
    cjk_chars = sum(1 for c in text if _is_cjk(c))
    latin_chars = len(text) - cjk_chars
    cjk_tokens = cjk_chars / CHARS_PER_TOKEN_CJK
    latin_tokens = latin_chars / CHARS_PER_TOKEN_LATIN
    return max(1, round(cjk_tokens + latin_tokens))


def count_tokens(text: str, use_tiktoken: bool = True) -> int:
    """Count tokens in text using tiktoken if available, else heuristic.

    Args:
        text: Input text.
        use_tiktoken: If True, prefer tiktoken for accurate counting.

    Returns:
        Token count (minimum 1).
    """
    if not text:
        return 1
    if use_tiktoken:
        enc = _get_tiktoken_encoder()
        if enc is not None:
            try:
                return max(1, len(enc.encode(text)))
            except Exception:
                pass
    return _estimate_heuristic(text)


def estimate_tokens(text: str) -> int:
    """Estimate tokens — uses tiktoken when available, else heuristic."""
    return count_tokens(text, use_tiktoken=True)


def estimate_cost(text: str, price_per_1m: float = 0.001) -> float:
    """Estimate cost for processing text.

    Args:
        text: Input text.
        price_per_1m: Price per 1M tokens.

    Returns:
        Estimated cost in the same currency as price_per_1m.
    """
    tokens = estimate_tokens(text)
    return tokens * price_per_1m / 1_000_000


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to approximately max_tokens."""
    if max_tokens <= 0:
        return ""
    current = estimate_tokens(text)
    if current <= max_tokens:
        return text
    enc = _get_tiktoken_encoder()
    if enc is not None:
        try:
            tokens = enc.encode(text)
            if len(tokens) <= max_tokens:
                return text
            return enc.decode(tokens[:max_tokens])
        except Exception:
            pass
    ratio = max_tokens / current
    cut_point = int(len(text) * ratio * 0.9)
    return text[:cut_point]


def has_tiktoken() -> bool:
    """Check if tiktoken is available for accurate token counting."""
    return _get_tiktoken_encoder() is not None
