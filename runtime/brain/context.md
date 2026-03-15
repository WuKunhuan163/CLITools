# Current Context

**Last updated:** 2026-03-10
**Working on:** Layered agent guidelines system (COMPLETED)
**Next step:** All pending tasks complete. Ready for next user request.
**Blocked on:** none

## Session Summary

Designed and implemented the layered agent guidelines system:

1. **Architecture** (`logic/agent/guidelines/`):
   - `engine.py` — `compose_guidelines(layers=[...])` merges base + layer modules
   - `base/conventions.py` — development norms (experience, exploration, quality, infrastructure)
   - `base/ecosystem.py` — structural knowledge (architecture, discovery, patterns, commands)
   - `layers/openclaw.py` — self-improvement loop (Error→Lesson→Skill→Tool→Hook)

2. **Integration**:
   - `ecosystem.py` auto-detects active layers (checks if `tool/OPENCLAW/` exists)
   - `brain_inject.py` injects guidelines into Cursor agent at session start
   - `format_guidelines()` renders guidelines as readable text for LLM context

3. **Design principles**:
   - Symmetric: both conventions and ecosystem categories are incrementable
   - Layered: TOOL base + OPENCLAW (or any future layer) stack additively
   - Located in `logic/` so both TOOL and OPENCLAW can directly import
