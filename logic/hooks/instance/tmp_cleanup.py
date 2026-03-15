"""Hook instance: tmp_cleanup

Fires periodically (via before_tool_call) to remind the agent to clean up
stale files in tmp/ directories. Linked to the tmp-test-script skill.

Triggers when:
- 10+ files exist in the root tmp/ directory
- Any file in tmp/ is older than 7 days
"""
from logic.hooks.engine import HookInstance


class TmpCleanupHook(HookInstance):
    name = "tmp_cleanup"
    description = "Remind agent to clean stale tmp/ files (linked to tmp-test-script skill)"
    event_name = "before_tool_call"
    enabled_by_default = True

    _last_check_call = 0
    _check_interval = 50  # check every 50 tool calls

    def execute(self, **kwargs):
        TmpCleanupHook._last_check_call += 1
        if TmpCleanupHook._last_check_call % self._check_interval != 1:
            return {}

        from pathlib import Path
        from datetime import datetime, timedelta

        tool = kwargs.get("tool")
        project_root = tool.project_root if tool else None
        if not project_root:
            return {}

        tmp_dir = Path(project_root) / "tmp"
        if not tmp_dir.is_dir():
            return {}

        now = datetime.now()
        cutoff = now - timedelta(days=7)
        total = 0
        stale = []

        for f in tmp_dir.iterdir():
            if f.name.startswith("."):
                continue
            total += 1
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    stale.append(f.name)
            except OSError:
                pass

        parts = []
        if total >= 10:
            parts.append(
                f"[tmp/ cleanup] {total} files in tmp/. "
                f"Review and delete files whose purpose is achieved. "
                f"See skill: tmp-test-script for cleanup rules."
            )
        if stale:
            names = ", ".join(stale[:5])
            suffix = f" (+{len(stale) - 5} more)" if len(stale) > 5 else ""
            parts.append(
                f"[tmp/ stale files] {len(stale)} files older than 7 days: "
                f"{names}{suffix}. Delete or promote them."
            )

        if parts:
            msg = " ".join(parts)
            return {
                "additional_context": msg,
                "followup_message": msg,
            }

        return {}
