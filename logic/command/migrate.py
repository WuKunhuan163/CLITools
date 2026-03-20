"""Backwards compatibility shim — real implementation is in logic/_/migrate/core.py."""

from logic._.migrate.core import (  # noqa: F401
    list_domains,
    get_domain_info,
    get_domain_module,
    check_pending,
    scan_domain,
    execute_migration,
    create_migrate_progress,
    get_turing_stage,
    MIGRATION_LEVELS,
    MIGRATE_DIR,
)
