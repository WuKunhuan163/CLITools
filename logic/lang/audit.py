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
        self.patterns = [
            # Standard _("key") or _('key')
            re.compile(r'\b_\(\s*f?["\']([^"\']+)["\']'),
            # Root get_translation(dir, "key", "default") - matches 2nd arg
            re.compile(r'(?<!\.)\bget_translation\([^,]+,\s*f?["\']([^"\']+)["\']'),
            # self.get_translation("key", "default") - matches 1st arg
            re.compile(r'\.get_translation\(\s*f?["\']([^"\']+)["\']')
        ]

    def audit(self, force_scan=False):
        """Perform the audit or return cached results."""
        if not self.lang_code:
            raise ValueError("lang_code must be specified for audit()")

        if not force_scan and self.cache_file and self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data, True
            except Exception:
                pass
        
        # Perform scan
        results = self._perform_scan()
        
        # Save to cache
        if self.cache_file:
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
        """Scan project for keys and check translation."""
        all_keys = {} # key -> {count: int, sources: [path], type: root|tool_name}
        
        for py_file in self.project_root.rglob("*.py"):
            # Exclude non-source directories
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

        translation_cache = {}
        def get_translation_data(path):
            if path in translation_cache:
                return translation_cache[path]
            data = {}
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception: pass
            translation_cache[path] = data
            return data

        audit_entries = []
        missing_translation = []
        duplicate_translations = {} # value -> [logical_paths]
        shadowed_keys = [] # [key, tool_name]
        
        supported_keys = 0
        total_references = 0
        supported_references = 0
        
        from logic.utils import get_logic_dir
        
        # Track root keys for shadowing check
        root_internal = get_logic_dir(self.project_root)
        root_json_path = root_internal / "translation" / f"{self.lang_code}.json"
        root_trans = get_translation_data(str(root_json_path))
        
        for key, info in all_keys.items():
            is_supported = False
            trans_file = ""
            logical_path = ""
            trans_val = ""
            
            if info["type"] == "root":
                logical_path = f"logic/translation/{self.lang_code}/{key}"
                if key in root_trans:
                    is_supported = True
                    trans_file = str(root_json_path.relative_to(self.project_root))
                    trans_val = root_trans[key]
                else:
                    mono_json_path = root_internal / "translation.json"
                    mono_trans = get_translation_data(str(mono_json_path))
                    if self.lang_code in mono_trans and key in mono_trans[self.lang_code]:
                        is_supported = True
                        trans_file = str(mono_json_path.relative_to(self.project_root))
                        trans_val = mono_trans[self.lang_code][key]
            else:
                # Check tool-local translation first
                tool_internal = get_logic_dir(self.project_root / "tool" / info["type"])
                tool_json_path = tool_internal / "translation.json"
                tool_dir_path = tool_internal / "translation" / f"{self.lang_code}.json"
                
                tool_trans = get_translation_data(str(tool_json_path))
                tool_dir_trans = get_translation_data(str(tool_dir_path))
                
                # Combine them for checking
                combined_tool_trans = {**tool_trans.get(self.lang_code, {}), **tool_dir_trans}
                if not combined_tool_trans:
                    # Try flat format
                    combined_tool_trans = {k: v for k, v in tool_trans.items() if isinstance(v, str)}

                logical_path = f"tool/{info['type']}/logic/translation/{self.lang_code}/{key}"
                
                # Shadowing check: ONLY if it's actually in the tool's translation
                if key in combined_tool_trans and key in root_trans:
                    shadowed_keys.append([key, info["type"]])
                
                if key in combined_tool_trans:
                    is_supported = True
                    trans_file = str(tool_dir_path.relative_to(self.project_root)) if tool_dir_path.exists() else str(tool_json_path.relative_to(self.project_root))
                    trans_val = combined_tool_trans[key]
                else:
                    # Fallback to root for tool descriptions if missing locally
                    if key in root_trans:
                        is_supported = True
                        trans_file = str(root_json_path.relative_to(self.project_root))
                        trans_val = root_trans[key]
                        # Correct logical path to root as it fell back
                        logical_path = f"logic/translation/{self.lang_code}/{key}"

            if not is_supported:
                missing_translation.append(logical_path)
            elif trans_val:
                # Track duplicate values
                if trans_val not in duplicate_translations:
                    duplicate_translations[trans_val] = []
                duplicate_translations[trans_val].append(logical_path)

            audit_entries.append({
                "key": key,
                "type": info["type"],
                "count": info["count"],
                "sources": info["sources"],
                "supported": is_supported,
                "translation_file": trans_file,
                "logical_path": logical_path,
                "value": trans_val
            })
            
            total_references += info["count"]
            if is_supported:
                supported_keys += 1
                supported_references += info["count"]

        # Filter real duplicates
        duplicates = {v: paths for v, paths in duplicate_translations.items() if len(paths) > 1}

        # Check for standalone 'en' files or sections
        en_violations = []
        for json_file in self.project_root.rglob("*.json"):
            if "venv" in json_file.parts or ".git" in json_file.parts: continue
            
            if json_file.name == "en.json":
                en_violations.append(str(json_file.relative_to(self.project_root)))
            elif json_file.name.endswith(".json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if "en" in data and isinstance(data["en"], (dict, str)):
                            en_violations.append(str(json_file.relative_to(self.project_root)))
                except: pass

        results = {
            "summary": {
                "total_keys": len(all_keys),
                "supported_keys": supported_keys,
                "total_references": total_references,
                "supported_references": supported_references,
                "completion_rate_keys": f"{(supported_keys/len(all_keys)*100):.1f}%" if all_keys else "100%",
                "completion_rate_refs": f"{(supported_references/total_references*100):.1f}%" if total_references else "100%",
                "missing_count": len(missing_translation),
                "duplicate_meanings_count": len(duplicates),
                "shadowed_keys_count": len(shadowed_keys),
                "en_violations_count": len(en_violations)
            },
            "missing": missing_translation,
            "duplicates": duplicates,
            "shadowed": shadowed_keys,
            "en_violations": en_violations,
            "entries": audit_entries,
            "timestamp": datetime.now().isoformat(),
            "lang_code": self.lang_code
        }
        return results
