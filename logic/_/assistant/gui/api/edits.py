"""File edit and hunk management endpoints."""
from __future__ import annotations
from pathlib import Path

_dir = Path(__file__).parent.parent
_root = _dir.parent.parent.parent


class EditsMixin:
    """File edit and hunk management endpoints."""

    def _revert_hunk(self, body: dict) -> dict:
        """Revert a single diff hunk by applying the inverse edit."""
        path = body.get("path", "").strip()
        old_text = body.get("old_text", "")
        new_text = body.get("new_text", "")
        hunk_index = body.get("hunk_index")
        session_id = body.get("session_id") or self._default_session_id

        if hunk_index is not None and session_id:
            return self._revert_hunk_by_index(session_id, hunk_index)

        if not path:
            return {"ok": False, "error": "Missing path"}

        import os
        if not os.path.isabs(path):
            cwd = self._mgr._get_cwd() if hasattr(self._mgr, '_get_cwd') else os.getcwd()
            path = os.path.join(cwd, path)

        try:
            content = open(path, encoding='utf-8', errors='replace').read()
            if old_text and old_text in content:
                new_content = content.replace(old_text, new_text, 1)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self._push_sse({"type": "hunk_reverted", "path": path,
                                "session_id": session_id})
                return {"ok": True, "path": path}
            elif not old_text and new_text:
                return {"ok": False, "error": "Cannot revert: added text not found in file"}
            else:
                return {"ok": False, "error": "Text to revert not found in file"}
        except FileNotFoundError:
            return {"ok": False, "error": f"File not found: {path}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _accept_hunk(self, body: dict) -> dict:
        """Accept (keep) a diff hunk — marks it decided without changing the file."""
        hunk_index = body.get("hunk_index")
        session_id = body.get("session_id") or self._default_session_id
        if hunk_index is None:
            return {"ok": False, "error": "Missing hunk_index"}

        blocks = self._get_edit_blocks(session_id)
        if hunk_index < 0 or hunk_index >= len(blocks):
            return {"ok": False, "error": f"hunk_index {hunk_index} out of range (0..{len(blocks)-1})"}

        block = blocks[hunk_index]
        if block.get("decided"):
            return {"ok": False, "error": f"Hunk {hunk_index} already decided as {block.get('decision')}"}

        block["decided"] = True
        block["decision"] = "accepted"
        self._push_sse({"type": "hunk_accepted", "hunk_index": hunk_index,
                        "path": block.get("path", ""), "session_id": session_id})
        return {"ok": True, "hunk_index": hunk_index, "path": block.get("path", "")}

    def _revert_hunk_by_index(self, session_id: str, hunk_index: int) -> dict:
        """Revert a hunk identified by its chronological index."""
        import os
        blocks = self._get_edit_blocks(session_id)
        if hunk_index < 0 or hunk_index >= len(blocks):
            return {"ok": False, "error": f"hunk_index {hunk_index} out of range (0..{len(blocks)-1})"}

        block = blocks[hunk_index]
        if block.get("decided"):
            return {"ok": False, "error": f"Hunk {hunk_index} already decided as {block.get('decision')}"}

        path = block.get("path", "")
        old_text = block.get("new_text", "")
        new_text = block.get("old_text", "")

        if not path:
            return {"ok": False, "error": "No path in hunk"}

        if not os.path.isabs(path):
            cwd = self._mgr._get_cwd() if hasattr(self._mgr, '_get_cwd') else os.getcwd()
            path = os.path.join(cwd, path)

        try:
            content = open(path, encoding='utf-8', errors='replace').read()
            if old_text and old_text in content:
                new_content = content.replace(old_text, new_text, 1)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                block["decided"] = True
                block["decision"] = "reverted"
                self._push_sse({"type": "hunk_reverted", "hunk_index": hunk_index,
                                "path": path, "session_id": session_id})
                return {"ok": True, "hunk_index": hunk_index, "path": path}
            else:
                return {"ok": False, "error": "Text to revert not found in file (file may have changed)"}
        except FileNotFoundError:
            return {"ok": False, "error": f"File not found: {path}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get_edit_blocks(self, session_id: str) -> list:
        """Return all edit blocks for a session, rebuilding from history each time."""
        if not hasattr(self, '_edit_blocks'):
            self._edit_blocks = {}
        old_blocks = self._edit_blocks.get(session_id, [])
        self._build_edit_blocks(session_id, old_blocks)
        return self._edit_blocks.get(session_id, [])

    def _build_edit_blocks(self, session_id: str, old_blocks: list = None):
        """Scan event history and build edit block list, preserving decision state."""
        events = self._event_history.get(session_id, [])
        old_decisions = {}
        if old_blocks:
            for b in old_blocks:
                if b.get("decided"):
                    key = (b.get("path", ""), b.get("old_text", "")[:50], b.get("new_text", "")[:50])
                    old_decisions[key] = b.get("decision")

        blocks = []
        for evt in events:
            if evt.get("type") == "tool_result" and evt.get("name") in ("edit_file", "write_file"):
                if not evt.get("ok"):
                    continue
                path = evt.get("_path", evt.get("path", ""))
                old_text = evt.get("_old_text", "")
                new_text = evt.get("_new_text", "")
                key = (path, old_text[:50], new_text[:50])
                decided = key in old_decisions
                decision = old_decisions.get(key)
                block = {
                    "index": len(blocks),
                    "tool": evt.get("name"),
                    "path": path,
                    "old_text": old_text,
                    "new_text": new_text,
                    "decided": decided,
                    "decision": decision,
                }
                blocks.append(block)
        if not hasattr(self, '_edit_blocks'):
            self._edit_blocks = {}
        self._edit_blocks[session_id] = blocks

    def _list_edit_blocks(self, session_id: str) -> dict:
        """Return edit blocks for CLI inspection."""
        if not session_id:
            return {"ok": False, "error": "No active session"}
        blocks = self._get_edit_blocks(session_id)
        summary = []
        for b in blocks:
            summary.append({
                "index": b["index"],
                "tool": b["tool"],
                "path": b.get("path", ""),
                "decided": b["decided"],
                "decision": b.get("decision"),
                "old_text_preview": (b.get("old_text", "") or "")[:80],
                "new_text_preview": (b.get("new_text", "") or "")[:80],
            })
        return {"ok": True, "blocks": summary, "count": len(summary)}

    def _read_file_lines(self, body: dict) -> dict:
        """Read specific lines from a file for streaming edit preview."""
        fpath = body.get("path", "")
        start = int(body.get("start", 1))
        end = int(body.get("end", start))
        if not fpath:
            return {"ok": False, "error": "Missing path"}
        try:
            if not os.path.isabs(fpath):
                fpath = os.path.join(os.getcwd(), fpath)
            with open(fpath, encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            total = len(all_lines)
            s = max(1, min(start, total))
            e = min(end, total)
            lines = [l.rstrip("\n") for l in all_lines[s-1:e]]
            return {"ok": True, "lines": lines, "total": total,
                    "start": s, "end": e}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

