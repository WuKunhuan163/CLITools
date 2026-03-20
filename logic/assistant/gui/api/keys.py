"""API key management endpoints."""
from __future__ import annotations
from pathlib import Path

_dir = Path(__file__).parent.parent
_root = _dir.parent.parent.parent


class KeysMixin:
    """API key management endpoints."""

    def _api_provider_guide(self, body: dict) -> dict:
        vendor = body.get("vendor", "").strip()
        if not vendor:
            return {"ok": False, "error": "Missing vendor parameter"}
        try:
            from tool.LLM.interface.main import get_provider_guide
            guide = get_provider_guide(vendor)
            return {"ok": True, "guide": guide}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _api_validate_key(self, body: dict) -> dict:
        vendor = body.get("vendor", "").strip()
        key = body.get("key", "").strip()
        if not vendor or not key:
            return {"ok": False, "error": "Missing vendor or key"}
        return self._validate_api_key(vendor, key)

    def _api_save_key(self, body: dict) -> dict:
        vendor = body.get("vendor", "").strip()
        key = body.get("key", "").strip()
        if not vendor or not key:
            return {"ok": False, "error": "Missing vendor or key"}
        from tool.LLM.logic.config import set_config_value
        set_config_value(f"{vendor}_api_key", key)
        self._push_sse({"type": "settings_changed", "action": "key_saved", "vendor": vendor})
        return {"ok": True}

    def _api_delete_key(self, body: dict) -> dict:
        vendor = body.get("vendor", "").strip()
        if not vendor:
            return {"ok": False, "error": "Missing vendor"}
        from tool.LLM.logic.config import set_config_value
        set_config_value(f"{vendor}_api_key", "")
        self._push_sse({"type": "settings_changed", "action": "key_deleted", "vendor": vendor})
        return {"ok": True}

    def _api_key_states(self, body: dict) -> dict:
        vendor = body.get("vendor", "").strip()
        if not vendor:
            return {"ok": False, "error": "Missing vendor"}
        from tool.LLM.logic.rate.key_state import get_selector
        sel = get_selector(vendor)
        return {"ok": True, "states": sel.get_all_states(),
                "has_usable": sel.has_usable_keys(),
                "active_count": sel.get_active_count()}

    def _api_reverify_key(self, body: dict) -> dict:
        vendor = body.get("vendor", "").strip()
        key_id = body.get("key_id", "").strip()
        if not vendor or not key_id:
            return {"ok": False, "error": "Missing vendor or key_id"}
        from tool.LLM.logic.rate.key_state import get_selector
        sel = get_selector(vendor)
        result = sel.reverify(key_id)
        if result.get("ok"):
            self._push_sse({"type": "settings_changed",
                            "action": "key_reverified", "vendor": vendor,
                            "key_id": key_id})
        return result

    def _api_key_reset_stale(self, body: dict) -> dict:
        """Reset all stale keys for a vendor back to active.

        If vendor is omitted or "*", resets all vendors.
        Also clears the in-memory selector cache to force reload.
        """
        vendor = (body or {}).get("vendor", "").strip()
        try:
            from tool.LLM.logic.rate.key_state import get_selector, _selectors, _sel_lock
            from tool.LLM.logic.registry import list_providers as list_reg_providers
            _ensure = lambda: None
            try:
                from tool.LLM.logic.registry import _ensure_builtins
                _ensure = _ensure_builtins
            except ImportError:
                pass

            _ensure()
            vendors_to_reset = []
            if not vendor or vendor == "*":
                seen = set()
                for p in list_reg_providers():
                    v = p.get("name", "").split("-")[0]
                    if v and v not in seen:
                        seen.add(v)
                        vendors_to_reset.append(v)
            else:
                vendors_to_reset = [vendor]

            reset_count = 0
            for v in vendors_to_reset:
                sel = get_selector(v)
                for kid, state in sel._states.items():
                    if state.status == "stale":
                        state.reactivate()
                        reset_count += 1
                sel._save()

            with _sel_lock:
                _selectors.clear()

            self._push_sse({"type": "settings_changed",
                            "action": "keys_reset", "count": reset_count})
            return {"ok": True, "reset_count": reset_count,
                    "vendors": vendors_to_reset}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _api_provider_status(self, body: dict) -> dict:
        """Return unified provider status from ProviderManager.

        Optional body params:
        - provider: single provider name (returns that provider only)
        - (no params): returns full snapshot of all providers
        """
        provider_name = body.get("provider", "").strip()
        try:
            from tool.LLM.logic.providers.manager import get_manager
            mgr = get_manager()
            if provider_name:
                return {"ok": True, "status": mgr.get_provider_status(provider_name)}
            return {"ok": True, "snapshot": mgr.get_full_snapshot()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Brain management endpoints ──

    @staticmethod
    def _validate_api_key(vendor: str, key: str) -> dict:
        """Validate an API key by making a minimal test request.

        On success, reactivates the key if it was previously stale.
        On auth failure, marks the key as stale.
        """
        VENDOR_PROVIDERS = {
            "zhipu": "zhipu-glm-4.7-flash",
            "google": "google-gemini-2.5-flash",
            "baidu": "baidu-ernie-4.5-turbo-128k",
            "tencent": "tencent-hunyuan-lite",
            "siliconflow": "siliconflow-qwen2.5-7b",
            "nvidia": "nvidia-glm-4-7b",
        }
        provider_name = VENDOR_PROVIDERS.get(vendor)
        if not provider_name:
            return {"ok": False, "error": f"Unknown vendor: {vendor}"}
        try:
            from tool.LLM.logic.registry import get_provider
            provider = get_provider(provider_name, api_key=key)
            result = provider._send_request(
                [{"role": "user", "content": "hi"}],
                temperature=0.1, max_tokens=5)

            try:
                from tool.LLM.logic.rate.key_state import get_selector
                from tool.LLM.logic.config import get_api_keys
                sel = get_selector(vendor)
                keys = get_api_keys(vendor)
                key_id = next((k["id"] for k in keys if k["key"] == key), None)
                if key_id:
                    sel.report(key_id, result)
                    if result.get("ok") or result.get("error_code") == 429:
                        state = sel._states.get(key_id)
                        if state and state.status == "stale":
                            state.reactivate()
                            sel._save()
            except Exception as e:
                _log.warning("Key health report failed: %s", e)

            if result.get("ok"):
                return {"ok": True, "model": result.get("model", provider_name)}
            if result.get("error_code") == 429:
                return {"ok": True, "model": result.get("model", provider_name),
                        "warning": "Key valid but rate limited (429). Quota may be exhausted."}
            if result.get("error_code") in (401, 403):
                return {"ok": False, "error": "Invalid API key (authentication failed)"}
            return {"ok": False, "error": result.get("error", "Validation failed")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

