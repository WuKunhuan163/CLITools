import os
import re
import json
from pathlib import Path
from datetime import datetime

class LangAuditor:
    def __init__(self, project_root, lang_code=None):
        self.project_root = Path(project_root)
        self.lang_code = lang_code
        self.audit_dir = self.project_root / "data" / "audit" / "lang"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        if lang_code:
            self.cache_file = self.audit_dir / f"audit_{lang_code}.json"
        else:
            self.cache_file = None
        
        # Regex patterns for finding translation keys
        # Use \b to avoid matching __import__ or other functions ending in _
        self.patterns = [
            re.compile(r'\b_\(\s*["\']([^"\']+)["\']'),
            re.compile(r'\bget_translation\([^,]+,\s*["\']([^"\']+)["\']')
        ]

    def audit(self, force_scan=False):
        """Perform the audit or return cached results."""
        if not self.lang_code:
            raise ValueError("lang_code must be specified for audit()")

        if not force_scan and self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data, True
            except Exception:
                pass
        
        # Perform scan
        results = self._perform_scan()
        
        # Save to cache
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
            
        return results, False

    def list_audited_languages(self):
        """List all languages that have audit files."""
        langs = []
        for audit_file in self.audit_dir.glob("audit_*.json"):
            lang_code = audit_file.name[6:-5] # audit_<lang>.json
            langs.append(lang_code)
        return sorted(langs)

    def _perform_scan(self):
        """Scan project for keys and check translations."""
        all_keys = {} # key -> {count: int, sources: [path], type: root|tool_name}
        
        for py_file in self.project_root.rglob("*.py"):
            # Exclude non-source directories and large installations
            parts = py_file.parts
            if any(p in parts for p in ["venv", ".git", "build", "dist", "tmp", "installations", "install", "node_modules", "bin", "resource", "data", "site-packages"]):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                for pattern in self.patterns:
                    for match in pattern.finditer(content):
                        key = match.group(1)
                        if key not in all_keys:
                            type_val = "root"
                            for part in py_file.parts:
                                if part == "tool" and len(py_file.parts) > py_file.parts.index(part) + 1:
                                    type_val = py_file.parts[py_file.parts.index(part) + 1]
                                    break
                            
                            all_keys[key] = {
                                "count": 0,
                                "sources": [],
                                "type": type_val
                            }
                        
                        all_keys[key]["count"] += 1
                        rel_path = str(py_file.relative_to(self.project_root))
                        if rel_path not in all_keys[key]["sources"]:
                            all_keys[key]["sources"].append(rel_path)
            except Exception:
                continue

        # Special case: Add dynamic keys from tool.json
        registry_path = self.project_root / "tool.json"
        if registry_path.exists():
            try:
                with open(registry_path, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                for tool_name in registry.get("tools", {}):
                    # Check if tool is installed
                    is_installed = (self.project_root / "tool" / tool_name).exists()
                    for key_suffix in ["desc", "purpose"]:
                        key = f"tool_{tool_name}_{key_suffix}"
                        if key not in all_keys:
                            all_keys[key] = {
                                "count": 1,
                                "sources": ["tool.json"],
                                "type": tool_name if is_installed else "root"
                            }
                        else:
                            all_keys[key]["count"] += 1
                            if "tool.json" not in all_keys[key]["sources"]:
                                all_keys[key]["sources"].append("tool.json")
            except Exception:
                pass

        translations_cache = {}
        
        def get_translations(path):
            if path in translations_cache:
                return translations_cache[path]
            data = {}
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception: pass
            translations_cache[path] = data
            return data

        audit_entries = []
        missing_translations = []
        supported_keys = 0
        total_references = 0
        supported_references = 0
        
        for key, info in all_keys.items():
            is_supported = False
            trans_file = ""
            logical_path = ""
            
            if info["type"] == "root":
                root_json_path = self.project_root / "proj" / "translation" / f"{self.lang_code}.json"
                root_trans = get_translations(str(root_json_path))
                logical_path = f"proj/translation/{self.lang_code}/{key}"
                
                if key in root_trans:
                    is_supported = True
                    trans_file = str(root_json_path.relative_to(self.project_root))
                else:
                    mono_json_path = self.project_root / "proj" / "translation.json"
                    mono_trans = get_translations(str(mono_json_path))
                    if self.lang_code in mono_trans and key in mono_trans[self.lang_code]:
                        is_supported = True
                        trans_file = str(mono_json_path.relative_to(self.project_root))
            else:
                # Check tool-local translations first
                tool_json_path = self.project_root / "tool" / info["type"] / "proj" / "translation.json"
                tool_trans = get_translations(str(tool_json_path))
                logical_path = f"tool/{info['type']}/proj/translation/{self.lang_code}/{key}"
                
                if self.lang_code in tool_trans and key in tool_trans[self.lang_code]:
                    is_supported = True
                    trans_file = str(tool_json_path.relative_to(self.project_root))
                elif key in tool_trans and isinstance(tool_trans[key], str):
                    is_supported = True
                    trans_file = str(tool_json_path.relative_to(self.project_root))
                else:
                    # Fallback to root for tool descriptions if missing locally
                    root_json_path = self.project_root / "proj" / "translation" / f"{self.lang_code}.json"
                    root_trans = get_translations(str(root_json_path))
                    if key in root_trans:
                        is_supported = True
                        trans_file = str(root_json_path.relative_to(self.project_root))

            if not is_supported:
                missing_translations.append(logical_path)

            audit_entries.append({
                "key": key,
                "type": info["type"],
                "count": info["count"],
                "sources": info["sources"],
                "supported": is_supported,
                "translation_file": trans_file,
                "logical_path": logical_path
            })
            
            total_references += info["count"]
            if is_supported:
                supported_keys += 1
                supported_references += info["count"]

        summary = {
            "language": self.lang_code,
            "timestamp": datetime.now().isoformat(),
            "total_keys": len(audit_entries),
            "supported_keys": supported_keys,
            "missing_keys": len(audit_entries) - supported_keys,
            "total_references": total_references,
            "supported_references": supported_references,
            "missing_references": total_references - supported_references,
            "completion_rate_keys": f"{(supported_keys / len(audit_entries) * 100):.2f}%" if audit_entries else "0%",
            "completion_rate_refs": f"{(supported_references / total_references * 100):.2f}%" if total_references else "0%"
        }
        
        return {
            "summary": summary,
            "missing_translations": sorted(missing_translations),
            "entries": audit_entries
        }
