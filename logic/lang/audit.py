import os
import re
import json
import ast
from pathlib import Path
from datetime import datetime
from logic.lang.utils import get_translation

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
        
        # Regex patterns for finding translation keys in code
        self.patterns = [
            # Standard _("key") or _('key')
            re.compile(r'\b_\(\s*f?["\']([^"\']+)["\']'),
            # Root get_translation(dir, "key", "default") - matches 2nd arg
            re.compile(r'(?<!\.)\bget_translation\([^,]+,\s*f?["\']([^"\']+)["\']'),
            # self.get_translation("key", "default") - matches 1st arg
            re.compile(r'\.get_translation\(\s*f?["\']([^"\']+)["\']'),
            # Custom helpers (like print_metric in main.py)
            re.compile(r'\bprint_metric\(\s*f?["\']([^"\']+)["\']')
        ]

    def audit_turing(self):
        """Scan project for Turing Machine state injections and generate a report."""
        audit_results = {} # hierarchical structure
        
        for py_file in self.project_root.rglob("*.py"):
            # Exclude non-source directories
            parts = py_file.parts
            if any(p in parts for p in ["venv", ".git", "build", "dist", "tmp", "installations", "install", "node_modules", "bin", "resource", "data", "site-packages"]):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if "TuringStage" not in content:
                        continue
                    tree = ast.parse(content)
            except Exception:
                continue

            file_stages = self._find_turing_stages(tree, py_file)
            if file_stages:
                # Build hierarchy
                curr = audit_results
                rel_parts = py_file.relative_to(self.project_root).parts
                for part in rel_parts[:-1]: # Folders
                    if part not in curr: curr[part] = {}
                    curr = curr[part]
                
                script_name = rel_parts[-1]
                curr[script_name] = file_stages

        # Save to data/audit/turing/audit_turing_<lang>.json
        turing_audit_dir = self.project_root / "data" / "audit" / "turing"
        turing_audit_dir.mkdir(parents=True, exist_ok=True)
        report_path = turing_audit_dir / f"audit_turing_{self.lang_code or 'en'}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(audit_results, f, indent=2, ensure_ascii=False)
            
        return audit_results, str(report_path)

    def _find_turing_stages(self, tree, file_path):
        """Find TuringStage instantiations in the AST."""
        stages = {} # line_number -> expected_output_dict
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check if it's a TuringStage call
                is_turing_stage = False
                if isinstance(node.func, ast.Name) and node.func.id == "TuringStage":
                    is_turing_stage = True
                elif isinstance(node.func, ast.Attribute) and node.func.attr == "TuringStage":
                    is_turing_stage = True
                
                if is_turing_stage:
                    stage_info = self._extract_stage_info(node, file_path)
                    if stage_info:
                        stages[node.lineno] = stage_info
        
        return stages

    def _extract_stage_info(self, node, file_path):
        """Extract and format strings from a TuringStage call node."""
        args = node.args
        keywords = {kw.arg: kw.value for kw in node.keywords}
        
        def get_val(idx, key, default):
            val_node = keywords.get(key)
            if val_node is None and len(args) > idx:
                val_node = args[idx]
            
            if val_node is None: return default
            return self._resolve_ast_value(val_node, file_path)

        # Replicate TuringStage defaults
        name = get_val(0, "name", "")
        active_status = get_val(2, "active_status", "Running")
        success_status = get_val(3, "success_status", "Successfully")
        fail_status = get_val(4, "fail_status", "Failed")
        success_color = get_val(5, "success_color", "GREEN")
        fail_color = get_val(6, "fail_color", "RED")
        active_name = get_val(8, "active_name", None)
        success_name = get_val(9, "success_name", None)
        fail_name = get_val(10, "fail_name", None)
        bold_part = get_val(11, "bold_part", None)

        # Simulation Logic (simplified ProgressTuringMachine.run formatting)
        BLUE = "\033[34m"
        BOLD = "\033[1m"
        RESET = "\033[0m"
        
        def format_state(status, n, color_code, bold_p):
            actual_n = n if n is not None else name
            full_no_format = f"{status} {actual_n}".strip() if actual_n else status
            # color_code from colors.json already includes BOLD
            if bold_p and full_no_format.startswith(bold_p):
                bold_text = bold_p
                rest_text = full_no_format[len(bold_p):].lstrip()
                return f"{color_code}{bold_text}{RESET}{' ' + rest_text if rest_text else ''}"
            elif actual_n:
                return f"{color_code}{status}{RESET} {actual_n}"
            else:
                return f"{color_code}{status}{RESET}"

        from logic.config import get_color
        green_code = get_color(success_color, "\033[32m") 
        red_code = get_color(fail_color, "\033[31m")
        
        expected_active = format_state(active_status, active_name, BLUE, bold_part) + "..."
        expected_success = format_state(success_status, success_name, green_code, bold_part)
        expected_fail = format_state(fail_status, fail_name, red_code, bold_part) + ". Reason: {brief_reason}."

        return {
            "active": expected_active,
            "success": expected_success,
            "fail": expected_fail
        }

    def _resolve_ast_value(self, node, file_path):
        """Resolve a string value from an AST node, handling translations."""
        if isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, (ast.Str, ast.Bytes)): # Older python versions
            return str(node.s)
        elif isinstance(node, ast.Call):
            # Check for _("key", "default")
            if isinstance(node.func, ast.Name) and node.func.id == "_":
                if node.args:
                    key_node = node.args[0]
                    default = ""
                    if len(node.args) > 1:
                        default = self._resolve_ast_value(node.args[1], file_path)
                    
                    key = self._resolve_ast_value(key_node, file_path)
                    # Try to translate
                    from logic.utils import get_logic_dir
                    target_dir = str(self.project_root / "logic")
                    for parent in Path(file_path).parents:
                        if (parent / "logic").is_dir():
                            target_dir = str(parent / "logic")
                            break
                    
                    res = get_translation(target_dir, key, default, lang_code=self.lang_code)
                    # If translation contains placeholders like {name}, keep them
                    return res
        elif isinstance(node, ast.JoinedStr):
            # Handle f-strings: just use placeholders for expressions
            parts = []
            for value in node.values:
                if isinstance(value, ast.FormattedValue):
                    parts.append("{v}")
                elif isinstance(value, ast.Constant):
                    parts.append(str(value.value))
            return "".join(parts)
        
        return "{v}"

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

    def _get_field_translation(self, field_id, default):
        """Helper to get translated field name/definition/advice."""
        try:
            from logic.utils import get_logic_dir
            logic_dir = get_logic_dir(self.project_root)
            key = f"audit_cat_{field_id}"
            return get_translation(str(logic_dir), key, default, lang_code=self.lang_code)
        except:
            return default

    def _get_line_number(self, file_path, key):
        """Get the line number of a key in a JSON file."""
        if not file_path.exists(): return 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    if f'"{key}"' in line:
                        return i
        except: pass
        return 0

    def _perform_scan(self):
        """Scan project for keys and check translation."""
        used_keys = {} # key -> {count: int, sources: [path], type: root|tool_name}
        
        # 1. Collect keys used in code
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
                        if key not in used_keys:
                            type_val = "root"
                            for part in py_file.parts:
                                if part == "tool" and len(py_file.parts) > py_file.parts.index(part) + 1:
                                    type_val = py_file.parts[py_file.parts.index(part) + 1]
                                    break
                            
                            used_keys[key] = {
                                "count": 0,
                                "sources": [],
                                "type": type_val
                            }
                        
                        used_keys[key]["count"] += 1
                        rel_path = str(py_file.relative_to(self.project_root))
                        if rel_path not in used_keys[key]["sources"]:
                            used_keys[key]["sources"].append(rel_path)
            except Exception:
                continue

        # Add dynamic keys from tool.json
        registry_path = self.project_root / "tool.json"
        if registry_path.exists():
            try:
                with open(registry_path, 'r', encoding='utf-8') as f:
                    registry = json.load(f)
                for tool_name in registry.get("tools", {}):
                    is_installed = (self.project_root / "tool" / tool_name).exists()
                    for key_suffix in ["desc", "purpose"]:
                        key = f"tool_{tool_name}_{key_suffix}"
                        if key not in used_keys:
                            used_keys[key] = {
                                "count": 1,
                                "sources": ["tool.json"],
                                "type": tool_name if is_installed else "root"
                            }
                        else:
                            used_keys[key]["count"] += 1
                            if "tool.json" not in used_keys[key]["sources"]:
                                used_keys[key]["sources"].append("tool.json")
            except Exception: pass

        # 2. Collect all defined keys in JSON files for the language
        defined_keys = {} # key -> list of {file_path, line, value}
        
        for json_file in self.project_root.rglob("*.json"):
            if any(p in json_file.parts for p in ["venv", ".git", "build", "dist", "tmp", "installations", "install", "node_modules", "data", "site-packages"]):
                continue
            
            # Check if this is a translation file for our lang_code
            is_trans_file = False
            if json_file.name == f"{self.lang_code}.json" and "translation" in json_file.parts:
                is_trans_file = True
            elif json_file.name == "translation.json":
                is_trans_file = True
                
            if not is_trans_file: continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Normalize data format
                target_trans = {}
                if self.lang_code in data and isinstance(data[self.lang_code], dict):
                    target_trans = data[self.lang_code]
                elif all(isinstance(v, str) for v in data.values()):
                    # Flat format, check if it belongs to this language based on file path or name
                    if json_file.name == f"{self.lang_code}.json" or "translation" in json_file.parts:
                        target_trans = data
                
                for k, v in target_trans.items():
                    if k not in defined_keys:
                        defined_keys[k] = []
                    rel_path = str(json_file.relative_to(self.project_root))
                    defined_keys[k].append({
                        "file_path": rel_path,
                        "line": self._get_line_number(json_file, k),
                        "value": v
                    })
            except: pass

        # 3. Analyze
        missing_entries = []
        duplicate_values = {} # value -> list of logical_paths
        duplicate_keys_entries = []
        unused_translations_entries = []
        shadowed_keys_entries = []
        en_violations_entries = []
        audit_entries = []
        
        # Root keys for shadowing
        root_defined_keys = set()
        for k, instances in defined_keys.items():
            if any("logic/translation" in inst["file_path"] for inst in instances):
                root_defined_keys.add(k)

        # Process used keys
        supported_keys_count = 0
        total_references = 0
        supported_references = 0
        
        for key, info in used_keys.items():
            total_references += info["count"]
            is_supported = key in defined_keys
            
            logical_path = ""
            trans_file = ""
            trans_val = ""
            
            if is_supported:
                # Pick the best instance (prefer local tool if it's a tool key)
                best_inst = defined_keys[key][0]
                if info["type"] != "root":
                    for inst in defined_keys[key]:
                        if f"tool/{info['type']}" in inst["file_path"]:
                            best_inst = inst
                            break
                
                trans_file = best_inst["file_path"]
                trans_val = best_inst["value"]
                logical_path = f"{trans_file.replace('.json', '')}/{key}"
                
                supported_keys_count += 1
                supported_references += info["count"]
                
                # Check shadowing
                if info["type"] != "root" and key in root_defined_keys:
                    # If it's defined in the tool path, it shadows root
                    if any(f"tool/{info['type']}" in inst["file_path"] for inst in defined_keys[key]):
                        shadowed_keys_entries.append({
                            "key": key,
                            "tool": info["type"],
                            "advice": f"Key '{key}' shadows a root translation. If the value is the same, consider removing it from tool translation."
                        })
                
                # Track values for duplicate values check
                if trans_val:
                    if trans_val not in duplicate_values:
                        duplicate_values[trans_val] = []
                    duplicate_values[trans_val].append(logical_path)
            else:
                missing_entries.append({
                    "key": key,
                    "type": info["type"],
                    "sources": info["sources"]
                })

            audit_entries.append({
                "key": key,
                "type": info["type"],
                "count": info["count"],
                "sources": info["sources"],
                "supported": is_supported,
                "translation_file": trans_file,
                "value": trans_val
            })

        # Process duplicate keys (same key in multiple files)
        for k, instances in defined_keys.items():
            if len(instances) > 1:
                duplicate_keys_entries.append({
                    "key": k,
                    "definitions": instances
                })

        # Process unused translations
        unused_to_delete = []
        for k, instances in defined_keys.items():
            # Protection: don't delete dynamic keys or audit internal keys
            if k.startswith("lang_name_") or k.startswith("audit_cat_") or k.startswith("col_") or k in ["label_found", "label_to", "label_asset"]:
                continue
                
            if k not in used_keys:
                for inst in instances:
                    unused_translations_entries.append({
                        "key": k,
                        "file_path": inst["file_path"],
                        "line": inst["line"]
                    })
                    # Add key for cleanup
                    inst_with_key = inst.copy()
                    inst_with_key['key'] = k
                    unused_to_delete.append(inst_with_key)

        # Process en violations
        for json_file in self.project_root.rglob("*.json"):
            if any(p in json_file.parts for p in ["venv", ".git", "build", "dist", "tmp", "installations", "install", "node_modules", "data", "site-packages"]):
                continue
            if json_file.name == "en.json":
                en_violations_entries.append({
                    "file_path": str(json_file.relative_to(self.project_root)),
                    "reason": "Standalone en.json file found."
                })
            else:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if "en" in data and isinstance(data["en"], (dict, str)):
                            en_violations_entries.append({
                                "file_path": str(json_file.relative_to(self.project_root)),
                                "reason": "JSON file contains 'en' section."
                            })
                except: pass

        # 4. Cleanup unused translations
        self._cleanup_unused(unused_to_delete)

        # 5. Format final result
        def make_cat(id, entries):
            return {
                "name": self._get_field_translation(f"{id}_name", id.replace("_", " ").title()),
                "definition": self._get_field_translation(f"{id}_def", ""),
                "advice": self._get_field_translation(f"{id}_advice", ""),
                "entries": entries
            }

        filtered_duplicate_values = {v: paths for v, paths in duplicate_values.items() if len(paths) > 1}

        results = {
            "summary": {
                "total_keys": len(used_keys),
                "supported_keys": supported_keys_count,
                "total_references": total_references,
                "supported_references": supported_references,
                "completion_rate_keys": f"{(supported_keys_count/len(used_keys)*100):.1f}%" if used_keys else "100%",
                "completion_rate_refs": f"{(supported_references/total_references*100):.1f}%" if total_references else "100%",
                "missing_count": len(missing_entries),
                "duplicate_values_count": len(filtered_duplicate_values),
                "duplicate_keys_count": len(duplicate_keys_entries),
                "shadowed_keys_count": len(shadowed_keys_entries),
                "unused_translations_count": len(unused_translations_entries),
                "en_violations_count": len(en_violations_entries)
            },
            "missing": make_cat("missing", missing_entries),
            "duplicate_values": make_cat("duplicate_values", filtered_duplicate_values),
            "duplicate_keys": make_cat("duplicate_keys", duplicate_keys_entries),
            "shadowed": make_cat("shadowed", shadowed_keys_entries),
            "unused_translations": make_cat("unused_translations", unused_translations_entries),
            "en_violations": make_cat("en_violations", en_violations_entries),
            "all_entries": audit_entries,
            "timestamp": datetime.now().isoformat(),
            "lang_code": self.lang_code
        }
        return results

    def _cleanup_unused(self, unused_instances):
        """Delete unused translation keys from JSON files."""
        # Group by file_path
        files_to_update = {}
        for inst in unused_instances:
            path = inst['file_path']
            if path not in files_to_update:
                files_to_update[path] = []
            files_to_update[path].append(inst['key'])
            
        for path_str, keys_to_remove in files_to_update.items():
            path = self.project_root / path_str
            if not path.exists(): continue
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                modified = False
                # If it's a multi-lang JSON with lang_code as top-level key
                if self.lang_code in data and isinstance(data[self.lang_code], dict):
                    for k in keys_to_remove:
                        if k in data[self.lang_code]:
                            del data[self.lang_code][k]
                            modified = True
                else:
                    # Single-lang JSON or direct keys
                    for k in keys_to_remove:
                        if k in data:
                            del data[k]
                            modified = True
                
                if modified:
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
            except: pass
