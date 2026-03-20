"""Status formatting interface for tools.

Provides standardized terminal output formatters that enforce the
minimal-emphasis rule (bold/color only on core phrases).
"""
from logic.utils.turing.status import (
    fmt_status,
    fmt_detail,
    fmt_stage,
    fmt_warning,
    fmt_info,
    get_cli_indent,
)

__all__ = [
    "fmt_status",
    "fmt_detail",
    "fmt_stage",
    "fmt_warning",
    "fmt_info",
    "get_cli_indent",
]
