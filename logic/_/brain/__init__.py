"""Brain module: pluggable memory architecture for AI agents.

Provides a three-tier memory system (working/knowledge/episodic) with
swappable backends and versioned blueprint definitions.

Structure:
    blueprint/   — Versioned blueprint packages (clitools, claude-mem, rag, openclaw)
    instance/    — Instance (session) management
    utils/       — Audit, validation, path safety analysis
    backends/    — Storage engine implementations (flatfile, planned: sqlite_fts, rag)
    loader.py    — Blueprint loading, base merging, backend instantiation
    base.py      — Abstract BrainBackend interface

Import from interface/brain.py, not directly from this module.
"""
