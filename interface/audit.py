"""Code quality audit interface.

Provides programmatic access to the code quality auditing system.
"""
from logic.audit.code_quality import (
    run_full_audit,
    print_report,
    AuditReport,
    Finding,
)

__all__ = [
    "run_full_audit",
    "print_report",
    "AuditReport",
    "Finding",
]
