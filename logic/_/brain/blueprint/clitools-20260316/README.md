# clitools-20260316

The project's default brain type. File-based, zero dependencies, full integration with the AITerminalTools ecosystem.

## Philosophy

Every piece of knowledge is a plain file. No databases, no embeddings, no external services. This makes the brain portable (zip and share), inspectable (read with any editor), and debuggable (grep for anything).

## Tiers

- **working**: context.md + tasks.json + activity.jsonl — session-scoped hot state
- **knowledge**: lessons.jsonl — permanent lesson store, managed by SKILLS
- **episodic**: SOUL.md + MEMORY.md + daily/ — agent personality and long-term memory

## Key Features

- BRAIN CLI integration (list, add, done, log, reflect, snapshot, recall, digest)
- Auto-generated MANIFEST.md for export/sharing
- Progressive context disclosure (L0 summaries in conversation)
- Hook-based IDE integration (Cursor: sessionStart, postToolUse, stop)

## When to Use

- Development workloads (the default for any new session)
- When zero dependencies is a requirement
- When the brain needs to be version-controlled in Git
- When portability (export/import) is important

## Upgrade Path

For larger knowledge bases (100+ lessons), consider `claude-mem-20260316` (better compression) or `rag-20260316` (semantic search).
