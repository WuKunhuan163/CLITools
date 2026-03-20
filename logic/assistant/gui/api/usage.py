"""Usage data and currency endpoints."""
from __future__ import annotations
from pathlib import Path

_dir = Path(__file__).parent.parent
_root = _dir.parent.parent.parent


class UsageMixin:
    """Usage data and currency endpoints."""

    @staticmethod
    def _get_currencies() -> dict:
        try:
            from interface.utils import list_currencies
            currencies = list_currencies()
            top_codes = ["USD", "EUR", "GBP", "CNY", "JPY", "KRW", "INR",
                         "CAD", "AUD", "CHF", "HKD", "SGD", "TWD", "BRL"]
            top = [c for c in currencies if c["code"] in top_codes]
            top.sort(key=lambda c: top_codes.index(c["code"]))
            rest = [c for c in currencies if c["code"] not in top_codes]
            return {"ok": True, "currencies": top + rest, "top_codes": top_codes}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get_usage_data(self) -> dict:
        """Aggregate usage data for Settings panel."""
        models = {}
        providers = {}
        from tool.LLM.logic.registry import list_models, list_providers as list_reg_providers
        from tool.LLM.logic.config import get_api_keys
        from interface.utils import to_usd, get_rates
        rates = get_rates()

        for m in list_models():
            mid = m["model"]
            cap = m.get("capabilities", {})
            model_json_path = os.path.join(
                str(_root), "tool", "LLM", "logic", "models",
                mid.replace("-", "_").replace(".", "_"), "model.json")
            cost_info = {}
            bench_info = {}
            free_tier = False
            active = True
            lock_reason = ""
            if os.path.exists(model_json_path):
                try:
                    with open(model_json_path) as f:
                        mj = json.load(f)
                    cost_info = mj.get("cost", {})
                    bench_info = mj.get("benchmarks", {})
                    free_tier = cost_info.get("free_tier", False)
                    active = mj.get("active", True)
                    lock_reason = mj.get("lock_reason", "")
                except Exception:
                    pass
            orig_currency = cost_info.get("currency", "USD")
            raw_input = cost_info.get("input_per_1m", cost_info.get("input_per_1k", 0) * 1000)
            raw_output = cost_info.get("output_per_1m", cost_info.get("output_per_1k", 0) * 1000)
            models[mid] = {
                "display_name": m.get("display_name", mid),
                "providers": m.get("providers", []),
                "capabilities": cap,
                "free_tier": free_tier,
                "input_price": to_usd(raw_input, orig_currency, rates),
                "output_price": to_usd(raw_output, orig_currency, rates),
                "currency": "USD",
                "benchmarks": bench_info,
                "active": active,
                "lock_reason": lock_reason,
                "total_calls": 0, "input_tokens": 0, "output_tokens": 0, "total_cost": 0,
            }

        available_providers = set()
        for p in list_reg_providers():
            pname = p.get("name", "")
            if pname == "auto":
                continue
            vendor = pname.split("-")[0] if pname else "unknown"
            if vendor not in providers:
                providers[vendor] = {
                    "models": [], "total_calls": 0,
                    "input_tokens": 0, "output_tokens": 0, "total_cost": 0,
                    "api_keys": [],
                }
            if pname not in providers[vendor]["models"]:
                providers[vendor]["models"].append(pname)
            try:
                keys = get_api_keys(vendor)
                try:
                    from tool.LLM.logic.rate.key_state import get_selector
                    sel = get_selector(vendor)
                    states = sel.get_all_states()
                    for k in keys:
                        st = states.get(k["id"], {})
                        k["state"] = st.get("status", "active")
                        k["state_reason"] = st.get("reason", "")
                except Exception:
                    pass
                providers[vendor]["api_keys"] = keys
                if keys:
                    available_providers.add(pname)
                    providers[vendor]["configured"] = True
            except Exception:
                pass

        for mid, mdata in models.items():
            mdata["configured"] = any(p in available_providers for p in mdata.get("providers", []))
            mdata["configured_providers"] = [p for p in mdata.get("providers", []) if p in available_providers]

        try:
            from tool.ARTIFICIAL_ANALYSIS.interface import get_rankings
            model_slugs = list(models.keys())
            aa_data = get_rankings(model_slugs)
            for our_slug, aa in aa_data.items():
                for mid in models:
                    if our_slug.lower() in mid.lower() or mid.lower() in our_slug.lower():
                        evals = aa.get("evaluations", {})
                        rankings = aa.get("rankings", {})
                        non_null_evals = {k: v for k, v in evals.items() if v is not None}
                        models[mid]["aa_benchmarks"] = non_null_evals
                        models[mid]["aa_benchmarks"]["_speed_tps"] = aa.get("speed")
                        models[mid]["aa_benchmarks"]["_ttft_s"] = aa.get("ttft")
                        models[mid]["aa_rankings"] = rankings
                        break
        except Exception:
            pass

        sorted_mids = sorted(models.keys(), key=len, reverse=True)
        for call in self._usage_calls:
            model_key = call.get("model", "")
            prov_key = call.get("provider", "")
            vendor = prov_key.split("-")[0] if prov_key else "unknown"
            inp = call.get("input_tokens", 0)
            outp = call.get("output_tokens", 0)

            for mid in sorted_mids:
                mdata = models[mid]
                provs = mdata.get("providers", [])
                if (mid == model_key
                        or model_key in provs
                        or prov_key in provs
                        or any(pr.endswith('-' + mid) for pr in [model_key, prov_key] if pr)):
                    mdata["total_calls"] += 1
                    mdata["input_tokens"] += inp
                    mdata["output_tokens"] += outp
                    break

            if vendor in providers:
                providers[vendor]["total_calls"] += 1
                providers[vendor]["input_tokens"] += inp
                providers[vendor]["output_tokens"] += outp

        from interface.utils import get_precision, get_symbol
        rate_info = {}
        for code in rates:
            rate_info[code] = {"rate": rates[code], "precision": get_precision(code), "symbol": get_symbol(code)}
        return {"models": models, "providers": providers, "calls": self._usage_calls[-100:], "rates": rate_info}

