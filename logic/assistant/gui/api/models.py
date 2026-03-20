"""Model listing, metadata, state, and icon resolution."""
from __future__ import annotations
from pathlib import Path

from tool.LLM.logic.naming import model_key_to_dir

_dir = Path(__file__).parent.parent
_root = _dir.parent.parent.parent


class ModelsMixin:
    """Model listing, metadata, state, and icon resolution."""

    def _api_switch_model(self, body: dict) -> dict:
        model = body.get("model", "").strip()
        if not model:
            return {"ok": False, "error": "Missing model"}
        if model != "auto":
            try:
                from tool.LLM.logic.registry import get_provider
                provider = get_provider(model)
                if not provider.is_available():
                    return {"ok": False, "error": f"Model {model} is not available"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        old_model = self._mgr._selected_model
        self._mgr._selected_model = model
        self.selected_model = model
        try:
            from tool.LLM.logic.base.auto import get_health
            get_health().mark_user_selected(model)
        except Exception as e:
            _log.warning("mark_user_selected failed: %s", e)
        self._push_sse({"type": "model_switched", "from": old_model, "to": model})
        return {"ok": True, "model": model}

    _i18n_cache: dict = {}

    def _api_i18n(self, body: dict | None) -> dict:
        """Return assistant GUI translation strings for a given language.

        GET  /api/i18n           -> all languages
        POST /api/i18n {lang:X}  -> single language
        """
        import json as _json
        trans_dir = _root / "logic" / "translation" / "assistant"
        if not trans_dir.is_dir():
            return {"ok": True, "translations": {}}

        if not self._i18n_cache:
            for f in trans_dir.iterdir():
                if f.suffix == ".json":
                    try:
                        self._i18n_cache[f.stem] = _json.loads(f.read_text())
                    except Exception:
                        pass

        lang = (body or {}).get("lang", "")
        if lang:
            return {"ok": True, "translations": {lang: self._i18n_cache.get(lang, {})}}
        return {"ok": True, "translations": self._i18n_cache}

    _palette_cache: dict | None = None

    def _api_palette(self) -> dict:
        """Return themes and palettes from the palette instance directory."""
        import json as _json
        if self._palette_cache is not None:
            return self._palette_cache

        palette_dir = _dir / "palette" / "instance"
        themes_dir = palette_dir / "themes"
        palettes_dir = palette_dir / "palettes"

        themes = []
        if themes_dir.is_dir():
            for f in themes_dir.iterdir():
                if f.suffix == ".json":
                    try:
                        themes.append(_json.loads(f.read_text()))
                    except Exception:
                        pass
            themes.sort(key=lambda t: t.get("order", 99))

        palettes = []
        if palettes_dir.is_dir():
            for f in palettes_dir.iterdir():
                if f.suffix == ".json":
                    try:
                        palettes.append(_json.loads(f.read_text()))
                    except Exception:
                        pass
            palettes.sort(key=lambda p: p.get("order", 99))

        result = {"ok": True, "themes": themes, "palettes": palettes}
        self._palette_cache = result
        return result

    def _api_model_state(self) -> dict:
        """Return the full selected/current state for model, mode, and turn limit.

        selected_*: What the user chose in the dropdown (takes effect at next boundary).
        current_*: What's actually running right now.
        Boundaries: model at round start, mode/turn_limit at task start.
        """
        mgr = self._mgr
        return {
            "ok": True,
            "selected_model": mgr._selected_model,
            "current_model": mgr._current_model,
            "selected_mode": mgr._selected_mode,
            "current_mode": mgr._current_mode,
            "selected_turn_limit": mgr._selected_turn_limit,
            "current_turn_limit": mgr._current_turn_limit,
            "auto_confirmed": getattr(mgr, '_auto_confirmed', False),
            "auto_retry_count": getattr(mgr, '_auto_retry_count', 0),
            "auto_tried": list(getattr(mgr, '_auto_tried', set())),
            "user_selection": mgr._selected_model,
            "active_model": mgr._current_model,
        }

    def _get_configured_models(self) -> dict:
        """Return models that have at least one configured+available provider.

        Inactive models are excluded from the dropdown list (but still
        appear in the settings panel with a locked indicator).
        """
        try:
            from tool.LLM.logic.registry import list_models, list_providers as list_reg_providers, _MODELS_DIR
            available_providers = set()
            for p in list_reg_providers():
                if p.get("available"):
                    available_providers.add(p.get("name", ""))

            meta_resp = self._api_models_metadata()
            model_meta = meta_resp.get("models", {}) if meta_resp.get("ok") else {}

            configured = [{"value": "auto", "label": "Auto"}]
            for m in list_models():
                mid = m["model"]
                provs = m.get("providers", [])
                has_key = any(p in available_providers for p in provs)

                model_dir = model_key_to_dir(mid)
                model_json_path = _MODELS_DIR / model_dir / "model.json"
                active = True
                lock_reason = ""
                if model_json_path.exists():
                    try:
                        import json as _json
                        mj = _json.loads(model_json_path.read_text())
                        active = mj.get("active", True)
                        lock_reason = mj.get("lock_reason", "")
                    except Exception:
                        pass

                if not active:
                    continue

                if has_key:
                    cost = m.get("cost", {})
                    mm = model_meta.get(mid, {})
                    configured.append({
                        "value": mid,
                        "label": mm.get("display_name") or m.get("display_name", mid),
                        "logo": mm.get("icon"),
                        "vendor": mm.get("vendor", ""),
                        "free_tier": cost.get("free_tier", False),
                        "input_price_per_1m": cost.get("input_per_1m", 0) or 0,
                        "output_price_per_1m": cost.get("output_per_1m", 0) or 0,
                        "currency": cost.get("currency", "USD"),
                    })
            return {"ok": True, "models": configured}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _api_models_metadata(self) -> dict:
        """Return model/provider/env metadata with local icon URLs and display names.

        Icon resolution order:
          1. Model directory logo.svg  (tool/LLM/logic/models/<dir>/logo.svg)
          2. Provider directory logo.svg (tool/LLM/logic/providers/<vendor>/logo.svg)
          3. Asset directory SVG fallback (logic/asset/image/models/ or providers/)
        """
        asset_root = _root / "logic" / "asset" / "image"
        llm_models_dir = _root / "tool" / "LLM" / "logic" / "models"
        llm_providers_dir = _root / "tool" / "LLM" / "logic" / "providers"

        def _asset_icon_url(subdir: str, name: str) -> str | None:
            fpath = asset_root / subdir / f"{name}.svg"
            if fpath.is_file():
                return f"/asset/icon/{subdir}/{name}.svg"
            return None

        provider_meta = {}
        if llm_providers_dir.is_dir():
            for d in llm_providers_dir.iterdir():
                if not d.is_dir() or d.name.startswith("_"):
                    continue
                pid = d.name
                logo = d / "logo.svg"
                if logo.is_file():
                    icon = f"/llm/providers/{pid}/logo.svg"
                else:
                    icon = _asset_icon_url("providers", pid)
                provider_meta[pid] = {"id": pid, "icon": icon}

        model_dir_logos = {}
        if llm_models_dir.is_dir():
            for d in llm_models_dir.iterdir():
                if not d.is_dir() or not (d / "logo.svg").is_file():
                    continue
                url = f"/llm/models/{d.name}/logo.svg"
                model_dir_logos[d.name] = url
                mj_path = d / "model.json"
                if mj_path.is_file():
                    try:
                        import json as _json
                        mj = _json.loads(mj_path.read_text())
                        for key in ("model_id", "api_model_id"):
                            v = mj.get(key, "")
                            if v:
                                model_dir_logos[v] = url
                                model_dir_logos[model_key_to_dir(v)] = url
                    except Exception:
                        pass

        # Fallback: asset/image/models/*.svg
        asset_model_icons = {}
        asset_models_dir = asset_root / "models"
        if asset_models_dir.is_dir():
            for f in asset_models_dir.iterdir():
                if f.suffix == ".svg":
                    asset_model_icons[f.stem] = f"/asset/icon/models/{f.stem}.svg"

        model_meta = {}
        try:
            from tool.LLM.logic.registry import list_models, _REGISTRY, _MODEL_PROVIDERS, _ensure_builtins
            _ensure_builtins()

            for m in list_models():
                mid = m["model"]
                vendor = m.get("vendor") or ""
                if not vendor:
                    parts = mid.split("-")
                    vendor = parts[0] if parts else ""
                display_name = m.get("display_name", mid)

                icon = self._resolve_model_icon(
                    mid, vendor, model_dir_logos,
                    asset_model_icons, provider_meta,
                )
                entry = {
                    "id": mid,
                    "display_name": display_name,
                    "vendor": vendor,
                    "icon": icon,
                }
                lb = m.get("logo_brightness")
                if lb is not None:
                    entry["logo_brightness"] = lb
                model_meta[mid] = entry

            for prov_name in _REGISTRY:
                if prov_name == "auto" or prov_name in model_meta:
                    continue
                for model_id, providers in _MODEL_PROVIDERS.items():
                    if prov_name in providers and model_id in model_meta:
                        model_meta[prov_name] = dict(model_meta[model_id])
                        model_meta[prov_name]["id"] = prov_name
                        break
        except Exception:
            pass

        env_meta = {
            "cursor": {"id": "cursor", "display_name": "Cursor", "icon": _asset_icon_url("providers", "cursor")},
            "copilot": {"id": "copilot", "display_name": "Copilot", "icon": _asset_icon_url("providers", "copilot")},
            "windsurf": {"id": "windsurf", "display_name": "Windsurf", "icon": _asset_icon_url("providers", "windsurf")},
        }

        mode_meta = {
            "meta-agent": {"icon": "bx-brain", "label": "Meta-Agent"},
            "agent": {"icon": "bx-bot", "label": "Agent"},
            "plan": {"icon": "bx-edit", "label": "Plan"},
            "ask": {"icon": "bx-chat", "label": "Ask"},
        }

        return {
            "ok": True,
            "providers": provider_meta,
            "models": model_meta,
            "env": env_meta,
            "modes": mode_meta,
        }

    @staticmethod
    def _resolve_model_icon(
        model_id: str,
        vendor: str,
        model_dir_logos: dict,
        asset_model_icons: dict,
        provider_meta: dict,
    ) -> str | None:
        """Pick the best icon for a model.

        Resolution order:
          1. Model directory logo.svg (model_dir_logos)
          2. Provider directory logo.svg (provider_meta[vendor].icon)
          3. Asset directory SVG fallback (asset_model_icons)
        """
        if model_id in model_dir_logos:
            return model_dir_logos[model_id]
        dir_name = model_key_to_dir(model_id)
        if dir_name in model_dir_logos:
            return model_dir_logos[dir_name]

        if vendor and vendor in provider_meta:
            picon = provider_meta[vendor].get("icon")
            if picon:
                return picon

        stem = model_id
        if stem in asset_model_icons:
            return asset_model_icons[stem]
        short = model_id.split("-", 1)[-1] if "-" in model_id else model_id
        if short in asset_model_icons:
            return asset_model_icons[short]
        family = short.rsplit("-", 1)[0] if "-" in short else short
        if family in asset_model_icons:
            return asset_model_icons[family]

        prefix = model_id.split("-")[0]
        if prefix in provider_meta:
            return provider_meta[prefix].get("icon")

        return None

    @staticmethod
    def _api_model_resolve(body: dict) -> dict:
        """Fuzzy-resolve a model/provider name query.

        Body: {"query": "ernie4.5-8k"} or {"query": "glm4flash"}
        Returns: {"ok": true, "resolved": "baidu-ernie-4.5-8k", "exact": false}
        """
        query = (body or {}).get("query", "").strip()
        if not query:
            return {"ok": False, "error": "Missing query"}
        try:
            from tool.LLM.logic.registry import (
                _resolve, _REGISTRY, _ALIASES, _ensure_builtins, fuzzy_resolve,
            )
            _ensure_builtins()
            exact = _resolve(query)
            if exact in _REGISTRY:
                return {"ok": True, "resolved": exact, "exact": True}
            fuzzy = fuzzy_resolve(query)
            if fuzzy:
                return {"ok": True, "resolved": fuzzy, "exact": False}
            return {"ok": False, "error": f"No match for '{query}'"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

