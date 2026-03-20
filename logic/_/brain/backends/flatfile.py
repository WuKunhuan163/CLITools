"""Flat-file brain backend (default).

Stores all data as plain files: .md for documents, .json for structured data,
.jsonl for append-only logs. Zero external dependencies.

This is the reference implementation. New backends (sqlite_fts, rag) should
maintain the same behavior guarantees.
"""
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from logic._.brain.base import BrainBackend


class FlatFileBrainBackend(BrainBackend):
    """File-based brain storage using markdown, JSON, and JSONL files."""

    def __init__(self, root: Path, blueprint: Dict):
        self.root = Path(root)
        self.blueprint = blueprint
        self._tier_paths = {}
        for tier_name, tier_config in blueprint.get("tiers", {}).items():
            self._tier_paths[tier_name] = self.root / tier_config.get("path", f"data/_/runtime/_/eco/brain/{tier_name}/")

    def _resolve_path(self, tier: str, key: str) -> Path:
        base = self._tier_paths.get(tier, self.root / "data" / "_" / "runtime" / "_" / "eco" / "brain")
        files = self.blueprint.get("tiers", {}).get(tier, {}).get("files", {})
        filename = files.get(key, key)
        return base / filename

    def store(self, tier: str, key: str, value: Any, metadata: Optional[Dict] = None) -> bool:
        path = self._resolve_path(tier, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, str):
            path.write_text(value, encoding="utf-8")
        elif isinstance(value, (dict, list)):
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            path.write_text(str(value), encoding="utf-8")
        return True

    def retrieve(self, tier: str, key: str) -> Any:
        path = self._resolve_path(tier, key)
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return content
        return content

    def search(self, query: str, tier: Optional[str] = None, top_k: int = 10) -> List[Dict]:
        results = []
        query_lower = query.lower()
        tiers = [tier] if tier else list(self._tier_paths.keys())
        for t in tiers:
            base = self._tier_paths.get(t)
            if not base or not base.exists():
                continue
            for file_path in base.rglob("*"):
                if not file_path.is_file():
                    continue
                if file_path.suffix == ".jsonl":
                    for line in file_path.read_text(encoding="utf-8").strip().split("\n"):
                        if not line.strip():
                            continue
                        if query_lower in line.lower():
                            try:
                                obj = json.loads(line)
                                results.append({"tier": t, "source": str(file_path.relative_to(self.root)), "entry": obj})
                            except json.JSONDecodeError:
                                results.append({"tier": t, "source": str(file_path.relative_to(self.root)), "text": line})
                elif file_path.suffix in (".md", ".json", ".txt"):
                    content = file_path.read_text(encoding="utf-8")
                    if query_lower in content.lower():
                        results.append({
                            "tier": t,
                            "source": str(file_path.relative_to(self.root)),
                            "preview": content[:200],
                        })
                if len(results) >= top_k:
                    return results[:top_k]
        return results[:top_k]

    def append(self, tier: str, key: str, entry: Dict) -> bool:
        path = self._resolve_path(tier, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if "timestamp" not in entry:
            entry["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return True

    def list_keys(self, tier: str) -> List[str]:
        base = self._tier_paths.get(tier)
        if not base or not base.exists():
            return []
        keys = []
        for file_path in sorted(base.rglob("*")):
            if file_path.is_file():
                keys.append(str(file_path.relative_to(base)))
        return keys
