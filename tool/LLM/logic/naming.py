"""LLM naming convention: single source of truth for model/provider name mapping.

Convention (MUST be followed by all model directories and model.json files):

  model_key:    Canonical human-readable ID with dots and hyphens.
                Used as the `model=` parameter in register().
                Examples: "ernie-4.5-8k", "qwen2.5-7b", "gemini-2.5-flash"

  dir_name:     Filesystem-safe name derived from model_key.
                Transformation: replace '.' with '_', replace '-' with '_'.
                Examples: "ernie_4_5_8k", "qwen2_5_7b", "gemini_2_5_flash"

  registry_name: Provider-scoped name = "<vendor>-<model_key>".
                Examples: "baidu-ernie-4.5-8k", "siliconflow-qwen2.5-7b"

  api_model_id: What the actual vendor API expects (may differ entirely).
                Stored in model.json under "api_model_id".
                Examples: "Qwen/Qwen2.5-7B-Instruct", "ernie-4.5-8k-preview"

  model.json fields:
    - "model_id": MUST equal model_key
    - "api_model_id": actual API identifier (omit if same as model_id)
    - "display_name": human-readable UI label

Reverse lookup:
  dir_name -> model_key is NOT lossless (underscores are ambiguous).
  Always use the forward direction: model_key -> dir_name.
  For reverse, use the model.json index.
"""
from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

_MODELS_DIR = Path(__file__).parent / "models"


def model_key_to_dir(model_key: str) -> str:
    """Convert a model_key to its directory name.

    >>> model_key_to_dir("ernie-4.5-8k")
    'ernie_4_5_8k'
    >>> model_key_to_dir("qwen2.5-7b")
    'qwen2_5_7b'
    >>> model_key_to_dir("gemini-3.1-flash-lite")
    'gemini_3_1_flash_lite'
    """
    return model_key.replace(".", "_").replace("-", "_")


def registry_name(vendor: str, model_key: str) -> str:
    """Build the registry name from vendor and model_key.

    >>> registry_name("baidu", "ernie-4.5-8k")
    'baidu-ernie-4.5-8k'
    """
    return f"{vendor}-{model_key}"


def model_dir_path(model_key: str) -> Path:
    """Return the absolute path to a model's directory."""
    return _MODELS_DIR / model_key_to_dir(model_key)


def find_model_dir(model_key: str) -> Optional[Path]:
    """Find the model directory, returning None if it doesn't exist."""
    p = model_dir_path(model_key)
    return p if p.is_dir() else None


def load_model_json(model_key: str) -> Optional[dict]:
    """Load model.json for a given model_key."""
    d = find_model_dir(model_key)
    if not d:
        return None
    mj = d / "model.json"
    if not mj.is_file():
        return None
    try:
        return json.loads(mj.read_text())
    except Exception:
        return None


def get_api_model_id(model_key: str) -> str:
    """Get the actual API model ID for a model_key.

    Falls back to model_key if api_model_id is not set.
    """
    mj = load_model_json(model_key)
    if mj:
        return mj.get("api_model_id") or mj.get("model_id") or model_key
    return model_key


# ── Fuzzy matching ──────────────────────────────────────────────────────


def _normalize(s: str) -> str:
    """Normalize a string for fuzzy comparison."""
    return s.lower().replace("_", "").replace("-", "").replace(".", "").replace(" ", "")


def fuzzy_match_model(query: str, known_keys: list[str],
                      threshold: float = 0.6) -> Optional[str]:
    """Find the best fuzzy match for a model query among known keys.

    Uses a combination of normalized exact prefix, subsequence, and
    SequenceMatcher ratio. Designed for Auto decision fault tolerance.

    Returns the best matching key, or None if nothing exceeds threshold.

    >>> fuzzy_match_model("ernie4.5-8k", ["ernie-4.5-8k", "ernie-5.0"])
    'ernie-4.5-8k'
    >>> fuzzy_match_model("qwen-2.5", ["qwen2.5-7b", "glm-4-flash"])
    'qwen2.5-7b'
    """
    if not query or not known_keys:
        return None

    q_norm = _normalize(query)

    # Phase 1: exact normalized match
    for key in known_keys:
        if _normalize(key) == q_norm:
            return key

    # Phase 2: prefix match on normalized form
    prefix_matches = []
    for key in known_keys:
        k_norm = _normalize(key)
        if k_norm.startswith(q_norm) or q_norm.startswith(k_norm):
            prefix_matches.append((key, max(len(q_norm), len(k_norm))))
    if prefix_matches:
        prefix_matches.sort(key=lambda x: x[1])
        return prefix_matches[0][0]

    # Phase 3: SequenceMatcher ratio
    best_key = None
    best_score = 0.0
    for key in known_keys:
        k_norm = _normalize(key)
        score = SequenceMatcher(None, q_norm, k_norm).ratio()
        if score > best_score:
            best_score = score
            best_key = key
    if best_score >= threshold:
        return best_key

    return None


def build_model_key_index() -> dict[str, str]:
    """Build an index mapping various name forms to canonical model_keys.

    Returns a dict where keys are various name forms (dir_name, model_id,
    api_model_id, normalized display_name) and values are the canonical
    model_key (from model.json "model_id").
    """
    index: dict[str, str] = {}
    if not _MODELS_DIR.is_dir():
        return index
    for d in _MODELS_DIR.iterdir():
        if not d.is_dir() or d.name.startswith("_"):
            continue
        mj_path = d / "model.json"
        if not mj_path.is_file():
            continue
        try:
            mj = json.loads(mj_path.read_text())
        except Exception:
            continue
        model_key = mj.get("model_id", "")
        if not model_key:
            continue
        index[model_key] = model_key
        index[d.name] = model_key
        index[model_key_to_dir(model_key)] = model_key
        api_id = mj.get("api_model_id", "")
        if api_id and api_id != model_key:
            index[api_id] = model_key
        dn = mj.get("display_name", "")
        if dn:
            index[dn.lower().replace(" ", "-")] = model_key
    return index
