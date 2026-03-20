"""Developer commands interface.

Provides tool development workflow commands.
"""
# TODO: [migration] This facade will be migrated/rewritten as part of the __/ architecture restructure.
from logic._.dev.commands import (
    dev_sync,
    dev_reset,
    dev_enter,
    dev_create,
    dev_scaffold_entrypoint,
    dev_sanity_check,
    dev_audit_test,
    dev_audit_bin,
    dev_migrate_bin,
    dev_audit_archived,
    dev_archive_tool,
    dev_unarchive_tool,
    dev_push_resource,
)
from logic._.dev.report import (
    list_docs,
    list_reports,
    view_file,
    create_report,
    edit_doc,
    find_provider_dir,
    provider_report,
)

__all__ = [
    "dev_sync",
    "dev_reset",
    "dev_enter",
    "dev_create",
    "dev_scaffold_entrypoint",
    "dev_sanity_check",
    "dev_audit_test",
    "dev_audit_bin",
    "dev_migrate_bin",
    "dev_audit_archived",
    "dev_archive_tool",
    "dev_unarchive_tool",
    "dev_push_resource",
    "list_docs",
    "list_reports",
    "view_file",
    "create_report",
    "edit_doc",
    "find_provider_dir",
    "provider_report",
]
