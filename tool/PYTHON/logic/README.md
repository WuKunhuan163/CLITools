# PYTHON Logic

Standalone Python environment manager. Handles discovery, installation, scanning, and updating of Python runtimes.

## Structure

| Module | Purpose |
|--------|---------|
| `config.py` | Path constants — project dirs, install/audit/resource paths |
| `install.py` | Python runtime installation (download, extract, verify) |
| `scanner.py` | Discover installed Python versions, audit system state |
| `update.py` | Check for and apply Python updates |
| `utils.py` | Platform detection, version parsing, display utilities |
