"""Code quality audit interface.

Provides programmatic access to the code quality auditing system,
import quality checking, and hooks/interface quality audits.
"""
from logic.audit.code_quality import (
    run_full_audit,
    print_report,
    AuditReport,
    Finding,
)
from logic.audit.utils import AuditManager
from logic.lang.audit_imports import (
    audit_all_tools as audit_imports_all,
    audit_tool as audit_imports_tool,
    audit_docs as audit_imports_docs,
    audit_root_files as audit_imports_root,
    format_report as format_imports_report,
    to_json as imports_to_json,
)
from logic.audit.hooks import (
    audit_all_quality,
    audit_tool_quality,
    audit_skills,
    format_quality_report,
    quality_to_json,
)

__all__ = [
    "run_full_audit",
    "print_report",
    "AuditReport",
    "Finding",
    "audit_imports_all",
    "audit_imports_tool",
    "audit_imports_docs",
    "audit_imports_root",
    "format_imports_report",
    "imports_to_json",
    "audit_all_quality",
    "audit_tool_quality",
    "audit_skills",
    "format_quality_report",
    "quality_to_json",
    "AuditManager",
]
