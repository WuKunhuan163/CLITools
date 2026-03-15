"""Text statistics and analysis utilities.

Provides basic text metrics like word count, sentence count, and character
distribution analysis for mixed CJK/Latin text.
"""

import re
from typing import Dict


def word_count(text: str) -> int:
    """Count the number of words in a text string.

    Words are defined as whitespace-separated tokens. Consecutive whitespace
    characters are treated as a single separator. Empty strings return 0.

    Args:
        text: Input text to analyze.

    Returns:
        Number of words (minimum 0).
    """
    if not text:
        return 0

    # Split by whitespace and filter out empty strings
    words = text.split()
    return len(words)


def sentence_count(text: str) -> int:
    """Count the number of sentences in a text string.

    Sentences are defined as text ending with ., !, or ? followed by
    whitespace or end of string. Multiple punctuation marks (e.g., "!!")
    are counted as one sentence end.

    Args:
        text: Input text to analyze.

    Returns:
        Number of sentences (minimum 0).
    """
    if not text:
        return 0

    # Match sentence-ending punctuation followed by whitespace or end
    # Use word boundaries to avoid matching punctuation within words
    pattern = r'[.!?]+(\s|$)'
    matches = re.findall(pattern, text)
    return len(matches)


def char_ratio(text: str) -> Dict[str, float]:
    """Calculate the ratio of CJK, Latin, and other characters.

    CJK characters are defined as Chinese, Japanese, and Korean characters
    (Unicode ranges: U+4E00-U+9FFF, U+3400-U+4DBF, U+F900-U+FAFF).

    Args:
        text: Input text to analyze.

    Returns:
        Dictionary with keys "cjk", "latin", and "other" containing ratios
        (float values between 0.0 and 1.0). Returns {0.0, 0.0, 0.0} for
        empty strings.
    """
    if not text:
        return {"cjk": 0.0, "latin": 0.0, "other": 0.0}

    cjk_count = 0
    latin_count = 0
    other_count = 0

    for char in text:
        # Skip whitespace characters
        if char.isspace():
            continue

        cp = ord(char)
        if (
            (0x4E00 <= cp <= 0x9FFF)
            or (0x3400 <= cp <= 0x4DBF)
            or (0xF900 <= cp <= 0xFAFF)
        ):
            cjk_count += 1
        elif char.isalpha() and char.isascii():
            latin_count += 1
        elif char.isalpha():
            other_count += 1

    total = cjk_count + latin_count + other_count
    if total == 0:
        return {"cjk": 0.0, "latin": 0.0, "other": 0.0}

    return {
        "cjk": cjk_count / total,
        "latin": latin_count / total,
        "other": other_count / total,
    }
