"""Artificial Analysis API client with local caching."""
import json
import os
import time
from typing import Dict, List, Optional
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

_API_BASE = "https://artificialanalysis.ai/api/v2"
_CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
_CACHE_FILE = _CACHE_DIR / "llm_models.json"
_DEFAULT_TTL = 24 * 3600


_CONFIG_FILE = Path(__file__).parent.parent / "data" / "config.json"


def _get_api_key() -> str:
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text()).get("api_key", "")
        except Exception:
            pass
    return os.environ.get("ARTIFICIAL_ANALYSIS_API_KEY", "")


def _load_cache() -> Optional[dict]:
    if _CACHE_FILE.exists():
        try:
            data = json.loads(_CACHE_FILE.read_text())
            age = time.time() - data.get("_cached_at", 0)
            if age < _DEFAULT_TTL:
                return data
        except Exception:
            pass
    return None


def _save_cache(data: dict):
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data["_cached_at"] = time.time()
    _CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def fetch_llm_models(force_refresh: bool = False, api_key: str = "") -> dict:
    """Fetch LLM model data from Artificial Analysis API.
    
    Returns dict with 'data' list of model objects.
    """
    if not force_refresh:
        cached = _load_cache()
        if cached:
            return cached

    key = api_key or _get_api_key()
    if not key:
        return {"error": "No API key configured. Set it in data/config.json or ARTIFICIAL_ANALYSIS_API_KEY env var."}

    url = f"{_API_BASE}/data/llms/models"
    req = Request(url, headers={"x-api-key": key, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        _save_cache(data)
        return data
    except HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except URLError as e:
        return {"error": f"Network error: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def get_model_benchmarks(model_slug: str, force_refresh: bool = False) -> Optional[dict]:
    """Get benchmarks for a specific model by slug or partial name match."""
    data = fetch_llm_models(force_refresh=force_refresh)
    if "error" in data:
        return data
    for m in data.get("data", []):
        slug = m.get("slug", "")
        name = m.get("name", "").lower()
        if slug == model_slug or model_slug.lower() in name or model_slug.lower() in slug:
            return m
    return None


def list_all_benchmarks(force_refresh: bool = False) -> List[dict]:
    """Return all models with their benchmarks, sorted by intelligence index."""
    data = fetch_llm_models(force_refresh=force_refresh)
    if "error" in data:
        return []
    models = data.get("data", [])
    return sorted(models,
                  key=lambda m: (m.get("evaluations", {}).get("artificial_analysis_intelligence_index") or 0),
                  reverse=True)


_VENDOR_PREFIXES = ("baidu-", "google-", "anthropic-", "openai-", "deepseek-",
                     "zhipu-", "tencent-", "siliconflow-", "nvidia-")

_MANUAL_SLUG_MAP = {
    "baidu-ernie-4.5-turbo-128k": "ernie-4-5-300b-a47b",
    "baidu-ernie-4.5-turbo-32k": "ernie-4-5-300b-a47b",
    "baidu-ernie-4.5-8k": "ernie-4-5-300b-a47b",
    "baidu-ernie-5.0": "ernie-5-0-thinking-preview",
    "baidu-ernie-x1.1": "ernie-5-0-thinking-preview",
    "deepseek-chat": "deepseek-v3-2",
    "deepseek-reasoner": "deepseek-r1",
    "anthropic-claude-haiku-4.5": "claude-4-5-haiku",
}


def _normalize_slug(s: str) -> str:
    """Normalize slug for fuzzy matching: strip vendor prefix, dots→dashes, trim suffixes."""
    s = s.lower().strip()
    for prefix in _VENDOR_PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    s = s.replace(".", "-")
    for suffix in ("-preview", "-latest", "-non-reasoning"):
        s = s.removesuffix(suffix)
    return s


def _match_aa_model(our_slug: str, aa_models: list) -> Optional[dict]:
    """Find best matching AA model for one of our model slugs."""
    if our_slug in _MANUAL_SLUG_MAP:
        target = _MANUAL_SLUG_MAP[our_slug]
        for m in aa_models:
            if m.get("slug") == target:
                return m

    norm = _normalize_slug(our_slug)
    best, best_score = None, 0
    for m in aa_models:
        aa_slug = m.get("slug", "")
        aa_norm = _normalize_slug(aa_slug)
        aa_name = m.get("name", "").lower().replace(".", "-")
        if norm == aa_norm:
            return m
        score = 0
        if norm in aa_norm or aa_norm in norm:
            score = max(len(norm), len(aa_norm))
        elif norm in aa_name:
            score = len(norm)
        if score > best_score:
            best, best_score = m, score
    return best if best_score >= 6 else None


def get_rankings_for_our_models(our_model_slugs: List[str], force_refresh: bool = False) -> Dict[str, dict]:
    """Get rankings relative to our supported models only.
    
    Returns {model_slug: {evaluations, pricing, rank_among_ours, ...}}
    """
    all_models = list_all_benchmarks(force_refresh=force_refresh)
    if not all_models:
        return {}

    slug_map = {}
    for our_slug in our_model_slugs:
        matched = _match_aa_model(our_slug, all_models)
        if matched:
            slug_map[our_slug] = matched

    all_eval_keys = set()
    for mdata in slug_map.values():
        for k, v in mdata.get("evaluations", {}).items():
            if v is not None:
                all_eval_keys.add(k)

    result = {}
    for metric in sorted(all_eval_keys):
        ranked = sorted(slug_map.items(),
                        key=lambda x: (x[1].get("evaluations", {}).get(metric) or 0),
                        reverse=True)
        for rank, (slug, mdata) in enumerate(ranked, 1):
            if slug not in result:
                result[slug] = {
                    "name": mdata.get("name", slug),
                    "slug": mdata.get("slug", ""),
                    "evaluations": mdata.get("evaluations", {}),
                    "pricing": mdata.get("pricing", {}),
                    "speed": mdata.get("median_output_tokens_per_second"),
                    "ttft": mdata.get("median_time_to_first_token_seconds"),
                    "rankings": {},
                }
            if (mdata.get("evaluations", {}).get(metric) or 0) > 0:
                result[slug]["rankings"][metric] = rank

    return result
