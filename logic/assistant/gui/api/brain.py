"""Brain instance management endpoints."""
from __future__ import annotations
from pathlib import Path

_dir = Path(__file__).parent.parent
_root = _dir.parent.parent.parent


class BrainMixin:
    """Brain instance management endpoints."""

    def _api_brain_blueprints(self) -> dict:
        """List all available brain blueprints."""
        try:
            from interface.brain import list_blueprints
            return {"ok": True, "blueprints": list_blueprints()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _api_brain_instances(self) -> dict:
        """List all brain instances (sessions)."""
        try:
            from interface.brain import get_session_manager
            sm = get_session_manager()
            return {"ok": True, "instances": sm.list_sessions()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _api_brain_active(self) -> dict:
        """Get the active brain instance and its blueprint type."""
        try:
            from interface.brain import get_session_manager
            sm = get_session_manager()
            name = sm.active_session()
            path = sm.session_path(name)
            bp_file = path / "blueprint.json"
            bp_type = "clitools-20260316"
            if bp_file.exists():
                import json as _j
                bp = _j.loads(bp_file.read_text(encoding="utf-8"))
                bp_type = bp.get("name", bp_type)
            return {
                "ok": True,
                "active": {
                    "name": name,
                    "blueprint_type": bp_type,
                    "path": str(path),
                    "exists": path.exists(),
                },
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _api_brain_create_instance(self, body: dict) -> dict:
        """Create a new brain instance from a blueprint."""
        name = body.get("name", "").strip()
        blueprint_type = body.get("blueprint_type", "").strip()
        if not name:
            return {"ok": False, "error": "Instance name is required"}
        try:
            from interface.brain import get_session_manager
            sm = get_session_manager()
            path = sm.create_session(name, brain_type=blueprint_type or None)
            return {"ok": True, "name": name, "path": str(path)}
        except FileExistsError:
            return {"ok": False, "error": f"Instance '{name}' already exists"}
        except FileNotFoundError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _api_brain_switch(self, body: dict) -> dict:
        """Switch the active brain instance."""
        name = body.get("name", "").strip()
        if not name:
            return {"ok": False, "error": "Instance name is required"}
        try:
            from interface.brain import get_session_manager
            sm = get_session_manager()
            sm.switch_session(name)
            return {"ok": True, "active": name}
        except FileNotFoundError:
            return {"ok": False, "error": f"Instance '{name}' not found"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _api_brain_audit(self, body: dict) -> dict:
        """Audit a brain blueprint for potential issues."""
        blueprint_name = body.get("blueprint", "").strip()
        if not blueprint_name:
            return {"ok": False, "error": "Blueprint name is required"}
        try:
            from interface.brain import audit_blueprint
            result = audit_blueprint(blueprint_name)
            return {"ok": True, "audit": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Sandbox endpoints ──

