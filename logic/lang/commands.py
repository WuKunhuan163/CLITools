import sys
from pathlib import Path
from typing import Optional, Callable

from logic.config import get_color
from logic.utils import get_logic_dir, get_rate_color, format_table
from logic.lang.utils import get_translation
from logic.audit.utils import AuditManager

def audit_lang(lang_code: str, project_root: Path, force: bool = False, turing: bool = False, translation_func: Optional[Callable] = None):
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    BOLD = get_color("BOLD", "\033[1m")
    BLUE = get_color("BLUE", "\033[34m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    if lang_code == "en" and not turing:
        print(_("audit_en_default", "English is the default language and does not require an audit scan."))
        return

    native_names = {"zh": "中文", "en": "English", "ar": "العربية"}
    lang_name = native_names.get(lang_code, get_translation(str(get_logic_dir(project_root)), f"lang_name_{lang_code}", lang_code, lang_code=lang_code))
    
    from logic.lang.audit import LangAuditor
    
    if turing:
        auditor = LangAuditor(project_root, lang_code)
        msg = _("audit_turing_scanning", "Scanning Turing Machine states for {lang} ({lang_name})...", lang=lang_code, lang_name=lang_name)
        print(f"{BLUE}{msg}{RESET}", end="", flush=True)
        results, report_path = auditor.audit_turing()
        sys.stdout.write(f"\r\033[K" + _("audit_turing_done", "Turing Machine state audit complete.") + "\n")
        
        report_label = _("audit_full_report_label", "Full report saved to")
        print(f"{BOLD}{report_label}{RESET}: {report_path}")
        return

    if force:
        p = project_root / "data" / "audit" / "lang" / f"audit_{lang_code}.json"
        if p.exists(): p.unlink()
    
    auditor = LangAuditor(project_root, lang_code)
    msg = _("audit_scanning", "Scanning translation coverage for {lang} ({lang_name})...", lang=lang_code, lang_name=lang_name)
    print(f"{BLUE}{msg}{RESET}", end="", flush=True)
    results, cached = auditor.audit()
    summary = results.get("summary", {})
    done_msg = _("audit_scanning_done", "Translation audit scan for {lang_name} complete.", lang_name=lang_name)
    sys.stdout.write(f"\r\033[K{done_msg}\n")
    sys.stdout.flush()
    
    rk, rr = summary.get("completion_rate_keys", "0%"), summary.get("completion_rate_refs", "0%")
    ck, cr = get_rate_color(rk), get_rate_color(rr)
    print(_("audit_summary_keys", "{rate} of keys support {lang} ({lang_name}) translation ({supported}/{total})", rate=f"{ck}{rk}{RESET}", supported=summary.get("supported_keys"), total=summary.get("total_keys"), lang=lang_code, lang_name=lang_name))
    print(_("audit_summary_refs", "{rate} of references support {lang} ({lang_name}) translation ({supported}/{total})", rate=f"{cr}{rr}{RESET}", supported=summary.get("supported_references"), total=summary.get("total_references"), lang=lang_code, lang_name=lang_name))
    
    def print_metric(key, count, color=None):
        if not count: return
        label = get_translation(str(get_logic_dir(project_root)), key, key.replace("_", " ").title(), lang_code=lang_code)
        parts = label.split(" ", 1)
        if len(parts) > 1:
            bold_part, rest_part = parts[0], " " + parts[1]
        else:
            bold_part, rest_part = label[:2], label[2:]
        
        print(f"{BOLD}{bold_part}{RESET}{rest_part}{RESET} ({count})")

    print_metric("audit_duplicate_values_label", summary.get("duplicate_values_count", 0))
    print_metric("audit_duplicate_keys_label", summary.get("duplicate_keys_count", 0))
    print_metric("audit_shadowed_label", summary.get("shadowed_keys_count", 0))
    print_metric("audit_unused_translations_label", summary.get("unused_translations_count", 0))
    print_metric("audit_en_violations_label", summary.get("en_violations_count", 0), color=RED)

    report_path = project_root / "data" / "audit" / "lang" / f"audit_{lang_code}.json"
    report_label = _("audit_full_report_label", "Full report saved to")
    print("\n" + f"{BOLD}{BLUE}{report_label}{RESET}: {report_path}")

    if cached:
        AuditManager(project_root / "data" / "audit" / "lang", component_name="LANG_AUDIT", audit_command=f"TOOL lang audit {lang_code}").print_cache_warning()

def list_languages(project_root: Path, translation_func: Optional[Callable] = None):
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    from logic.lang.audit import LangAuditor
    import json
    
    supported = ["en"]
    trans_dir = project_root / "logic" / "translation"
    if trans_dir.exists():
        for p in trans_dir.glob("*.json"):
            if p.stem not in supported: supported.append(p.stem)
    
    current_lang = "en"
    config_path = project_root / "data" / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f: current_lang = json.load(f).get("language", "en")
        except: pass
    
    native_names = {"zh": "中文 (zh)", "en": "English (en)", "ar": "العربية (ar)"}
    rows = []
    for lang in sorted(supported):
        if lang == "en":
            rows.append({"code": "en", "name": native_names.get("en", "English (en)"), "keys": _("lang_default", "default"), "refs": _("lang_default", "default"), "is_current": current_lang == "en"})
            continue
        res, cached = LangAuditor(project_root, lang).audit()
        if res:
            summary = res.get("summary", {})
            rk, rr = summary.get("completion_rate_keys", "0%"), summary.get("completion_rate_refs", "0%")
            ck, cr = get_rate_color(rk), get_rate_color(rr)
            keys_val, refs_val = f"{ck}{rk}{get_color('RESET')}", f"{cr}{rr}{get_color('RESET')}"
        else:
            keys_val, refs_val = "N/A", "N/A"
        name = native_names.get(lang, _(f"lang_name_{lang}", lang))
        rows.append({"code": lang, "name": name, "keys": keys_val, "refs": refs_val, "is_current": current_lang == lang})
    
    headers = [_("lang_table_name", "Language"), _("lang_table_keys", "Key Coverage"), _("lang_table_refs", "Ref Coverage")]
    table_rows = [[r['name'], r["keys"], r["refs"] + (" *" if r["is_current"] else "")] for r in rows]
    from logic.turing.display.manager import _get_configured_width
    width = _get_configured_width()
    table_str, _ = format_table(headers, table_rows, max_width=width if width > 0 else None, save_dir="lang")
    print("\n" + _("lang_list_header", "Supported Languages:") + "\n" + table_str)

