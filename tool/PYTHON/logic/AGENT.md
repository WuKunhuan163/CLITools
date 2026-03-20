# PYTHON Logic — Technical Reference

## Key Paths (config.py)

- `DATA_DIR`: `tool/PYTHON/data/` — runtime data
- `INSTALL_DIR`: `tool/PYTHON/data/install/` — downloaded Python binaries
- `AUDIT_DIR`: `tool/PYTHON/data/_/audit/` — scan/audit results
- `RESOURCE_ROOT`: `logic/_/install/resource/PYTHON/data/install/` — bundled installers

## install.py

Downloads and installs Python from python.org or bundled resources:
- Version-aware download with hash verification
- Platform-specific handling (macOS .pkg, Linux tarball, Windows .exe)
- Progress display via TuringMachine

## scanner.py

Discovers all Python installations on the system:
- Scans common paths (`/usr/bin`, `/usr/local/bin`, Homebrew, pyenv, etc.)
- Reports version, path, architecture, symlink targets
- Uses `AuditManager` to store scan results

## update.py

Checks for available Python updates and applies them:
- Compares installed vs. latest available version
- Downloads and installs updates with rollback capability

## utils.py

Platform utilities:
- `get_system_tag()`: Returns platform identifier for download URLs
- `regularize_version_name()`: Normalizes version strings
- `truncate_to_display_width()`: Terminal-safe string truncation

## Gotchas

1. **`logic_internal` import**: `utils.py` tries to import from `logic_internal.lang.utils` — a legacy path. Falls back to `interface.lang`.
2. **sys.path manipulation**: Several modules manually fix `sys.path[0]` to avoid the tool's `logic/` shadowing root `logic/`. Use `logic.resolve.setup_paths` in new code.
