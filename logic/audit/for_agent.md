# logic/audit - Agent Reference

> **Import convention**: Tools should import from `interface.audit` (the facade), not directly from `logic.audit`. See `interface/for_agent.md`.

## Key Interfaces

### code_quality.py
- `run_full_audit(project_root, exclude_patterns)` - Runs ruff + vulture across the project; returns `AuditReport`
- `print_report(report)` - Renders color-coded audit results to terminal
- `AuditReport` / `Finding` - Dataclasses for audit results

### utils.py
- Re-exports all from `logic.tool.audit.utils`
- Canonical implementation: `logic.tool.audit.utils`
- Provides `AuditManager` and audit-related utilities for tool audit commands

## Usage

```python
from interface.audit import run_full_audit, print_report
```
