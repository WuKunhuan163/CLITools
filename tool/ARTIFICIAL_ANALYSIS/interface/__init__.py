"""Artificial Analysis tool interface.

Provides benchmark data for LLM models from Artificial Analysis API.
"""
from typing import Dict, List, Optional


def fetch_benchmarks(force_refresh: bool = False, api_key: str = "") -> dict:
    """Fetch all LLM benchmark data. Returns cached data if available."""
    from tool.ARTIFICIAL_ANALYSIS.logic.client import fetch_llm_models
    return fetch_llm_models(force_refresh=force_refresh, api_key=api_key)


def get_model_data(model_slug: str, force_refresh: bool = False) -> Optional[dict]:
    """Get benchmark data for a specific model."""
    from tool.ARTIFICIAL_ANALYSIS.logic.client import get_model_benchmarks
    return get_model_benchmarks(model_slug, force_refresh=force_refresh)


def get_rankings(our_model_slugs: List[str], force_refresh: bool = False) -> Dict[str, dict]:
    """Get rankings relative to our configured models only."""
    from tool.ARTIFICIAL_ANALYSIS.logic.client import get_rankings_for_our_models
    return get_rankings_for_our_models(our_model_slugs, force_refresh=force_refresh)
