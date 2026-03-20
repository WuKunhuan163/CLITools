"""Enterprise-grade JSON repair for LLM tool call arguments.

Handles common malformations from various LLM providers:
- Unquoted or single-quoted keys/values
- Trailing commas, missing commas
- Special tokens (<|call|>, <|endoftext|>, etc.)
- Mixed quote styles (single + double)
- Escaped newlines as literal \\n vs actual newlines
- Truncated JSON (missing closing braces)
- Markdown code fences around JSON
- Python-style dict syntax (single quotes, True/False/None)
- Extra trailing quotes or garbage after valid JSON
"""
import json
import re


def repair_and_parse(raw: str) -> dict:
    """Parse tool arguments with multi-layer repair."""
    if not raw or not raw.strip():
        return {}

    raw = raw.strip()

    # Layer 1: direct parse
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Layer 2: structural repair then parse
    repaired = _repair_json(raw)
    try:
        result = json.loads(repaired)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Layer 3: regex key-value extraction
    return _regex_extract(raw)


def _repair_json(raw: str) -> str:
    """Apply structural repairs to malformed JSON."""
    s = raw

    # Strip LLM special tokens
    s = re.sub(r'<\|[^|]*\|>', '', s)

    # Strip markdown code fences
    s = re.sub(r'^```(?:json)?\s*\n?', '', s)
    s = re.sub(r'\n?```\s*$', '', s)

    # Strip leading/trailing non-JSON content (e.g. "}" at end, extra quotes)
    s = s.strip()
    if not s.startswith('{'):
        idx = s.find('{')
        if idx >= 0:
            s = s[idx:]
    # Find the matching closing brace
    s = _extract_first_json_object(s)

    # Fix Python-style True/False/None
    s = re.sub(r'\bTrue\b', 'true', s)
    s = re.sub(r'\bFalse\b', 'false', s)
    s = re.sub(r'\bNone\b', 'null', s)

    # Fix single-quoted strings to double-quoted
    s = _fix_single_quotes(s)

    # Fix trailing commas before } or ]
    s = re.sub(r',\s*([}\]])', r'\1', s)

    # Fix missing closing brace
    opens = s.count('{') - s.count('}')
    if opens > 0:
        s += '}' * opens
    opens_sq = s.count('[') - s.count(']')
    if opens_sq > 0:
        s += ']' * opens_sq

    # Fix unquoted keys: word: -> "word":
    s = re.sub(r'(?<=\{|,)\s*(\w+)\s*:', r' "\1":', s)

    return s


def _extract_first_json_object(s: str) -> str:
    """Extract the first balanced JSON object from a string."""
    if not s.startswith('{'):
        return s
    depth = 0
    in_str = False
    escape = False
    for i, c in enumerate(s):
        if escape:
            escape = False
            continue
        if c == '\\' and in_str:
            escape = True
            continue
        if c == '"' and not escape:
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return s[:i + 1]
    return s


def _fix_single_quotes(s: str) -> str:
    """Convert single-quoted JSON strings to double-quoted.

    Handles nested quotes carefully by tracking state.
    """
    result = []
    i = 0
    in_double = False
    in_single = False

    while i < len(s):
        c = s[i]

        if i > 0 and s[i - 1] == '\\':
            result.append(c)
            i += 1
            continue

        if c == '"' and not in_single:
            in_double = not in_double
            result.append(c)
        elif c == "'" and not in_double:
            if not in_single:
                in_single = True
                result.append('"')
            else:
                in_single = False
                result.append('"')
        elif c == '"' and in_single:
            result.append('\\"')
        else:
            result.append(c)

        i += 1

    return ''.join(result)


_KNOWN_KEYS = (
    "path", "command", "pattern", "old_text", "new_text",
    "content", "question", "thought", "action", "items",
    "start_line", "end_line", "query",
)


def _regex_extract(raw: str) -> dict:
    """Last-resort: extract key-value pairs using regex patterns."""
    args = {}

    for key in _KNOWN_KEYS:
        val = _extract_value(raw, key)
        if val is not None:
            if key in ("start_line", "end_line"):
                try:
                    args[key] = int(val)
                except ValueError:
                    args[key] = val
            else:
                args[key] = val

    return args


def _extract_value(raw: str, key: str) -> str | None:
    """Extract a single key's value from malformed JSON using multiple strategies."""
    # Strategy 1: "key": "value" (standard)
    pattern = rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"'
    m = re.search(pattern, raw)
    if m:
        return _unescape(m.group(1))

    # Strategy 2: "key": 'value' (single-quoted)
    pattern_sq = rf'"{key}"\s*:\s*\'((?:[^\'\\]|\\.)*)\''
    m = re.search(pattern_sq, raw)
    if m:
        return _unescape(m.group(1))

    # Strategy 3: "key": number (for start_line, end_line)
    pattern_num = rf'"{key}"\s*:\s*(\d+)'
    m = re.search(pattern_num, raw)
    if m:
        return m.group(1)

    # Strategy 4: key: "value" (unquoted key)
    pattern_uq = rf'\b{key}\b\s*:\s*"((?:[^"\\]|\\.)*)"'
    m = re.search(pattern_uq, raw)
    if m:
        return _unescape(m.group(1))

    return None


def _unescape(val: str) -> str:
    """Unescape common JSON escape sequences."""
    val = val.replace("\\n", "\n")
    val = val.replace("\\t", "\t")
    val = val.replace('\\"', '"')
    val = val.replace("\\'", "'")
    val = val.replace("\\\\", "\\")
    return val
