"""Generate the LLM usage dashboard HTML with live data.

Reads usage records and provider info, embeds them as JSON into the
HTML template, and writes the result to a standalone HTML file.
"""
import json
import datetime
from pathlib import Path
from typing import Dict, Any

_DIR = Path(__file__).resolve().parent
_TEMPLATE = _DIR / "template.html"
_DATA_DIR = _DIR.parent.parent / "data"
_OUTPUT = _DATA_DIR / "dashboard.html"


def _get_providers() -> list:
    from tool.LLM.logic.registry import list_providers
    return list_providers()


def _get_records() -> list:
    from tool.LLM.logic.usage import load_records
    records = load_records()
    return [
        {
            "timestamp": r.timestamp,
            "provider": r.provider,
            "model": r.model,
            "ok": r.ok,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "total_tokens": r.total_tokens,
            "latency_s": r.latency_s,
            "error": r.error,
            "error_code": r.error_code,
            "estimated_cost_usd": r.estimated_cost_usd,
            "api_key_masked": r.api_key_masked,
        }
        for r in records
    ]


def _get_api_keys() -> Dict[str, str]:
    """Get masked API keys per provider."""
    from tool.LLM.logic.config import load_config
    cfg = load_config()
    result = {}
    key_map = {
        "nvidia-glm-4-7b": "nvidia_api_key",
        "zhipu-glm-4-flash": "zhipu_api_key",
        "zhipu-glm-4.7": "zhipu_api_key",
    }
    for provider, cfg_key in key_map.items():
        key = cfg.get(cfg_key, "")
        if key:
            result[provider] = key
    return result


def _enrich_costs(records: list, providers: list):
    """Add estimated_cost_usd to each record based on provider cost models."""
    cost_models = {}
    for p in providers:
        cm = p.get("cost_model", {})
        prompt_price = cm.get("prompt_price_per_m", 0) or 0
        completion_price = cm.get("completion_price_per_m", 0) or 0
        cost_models[p["name"]] = (prompt_price, completion_price)

    for r in records:
        pp, cp = cost_models.get(r["provider"], (0, 0))
        r["estimated_cost_usd"] = (
            r["prompt_tokens"] * pp / 1_000_000
            + r["completion_tokens"] * cp / 1_000_000
        )


def _get_provider_limits() -> Dict[str, Any]:
    from tool.LLM.logic.usage import get_all_provider_limits
    return get_all_provider_limits()


def generate(output_path: str = "") -> str:
    """Generate the dashboard HTML and return the output path."""
    providers = _get_providers()
    records = _get_records()
    api_keys = _get_api_keys()
    limits = _get_provider_limits()

    _enrich_costs(records, providers)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data = {
        "providers": providers,
        "records": records,
        "api_keys": api_keys,
        "provider_limits": limits,
        "generated_at": now,
    }

    template = _TEMPLATE.read_text(encoding="utf-8")
    data_json = json.dumps(data, ensure_ascii=False, default=str)
    html = template.replace("__DASHBOARD_DATA__", data_json)

    out = Path(output_path) if output_path else _OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out)
