# Code Decomposition & Ecosystem Hardening

**Date**: 2026-03-18
**Context**: Continuation of code decomposition work from previous session. Major focus on USERINPUT enforcement, module decomposition, hooks migration, and report system.

## USERINPUT Enforcement Overhaul

Root cause analysis of USERINPUT being killed by previous agent:

1. **userinput_flag.py** set the flag too early (on command start, not completion)
2. No rule explicitly stated USERINPUT is not replaceable by Cursor Chat
3. No rule prohibited killing USERINPUT

**Fixes applied:**
- Updated userinput_flag.py: only sets flag on exit_code 0, detects kill commands, clears flag on kill
- Updated userinput_enforce.py: stronger messaging about USERINPUT vs Cursor Chat
- Updated all rules (.cursor/rules/*.mdc): added NOT Cursor Chat, NEVER kill sections
- Updated USERINPUT AGENT.md: comparison table, anti-kill section
- Updated userinput-feedback-loop skill: added Section 0 (NEVER kill)
- Updated brain_inject.py: stronger USERINPUT section in session start context

## Module Decomposition

### logic/_/setup/userinput/ -> decomposed
- UNIVERSAL_PROMPTS, PROJECT_PROMPTS -> tool/USERINPUT/logic/prompts.py
- IDE_CURSOR_PROMPTS -> logic/_/setup/IDE/cursor/prompts.py
- get_default_prompts() -> tool/USERINPUT/logic/prompts.py (imports IDE from setup)
- interface/tool.py updated to import from new location
- Old module deleted

### logic/_/setup/engine.py -> partial decomposition
- fetch_resource() extracted to logic/_/dev/resource.py
- engine.py re-exports for backward compatibility
- interface/tool.py imports from canonical location

## Hooks Migration

Moved root hooks/ directory into logic/_/hooks/IDE/Cursor/:
- Scripts: brain_inject.py, brain_remind.py, userinput_flag.py, userinput_enforce.py, file_search_fallback.py
- Updated .cursor/hooks.json paths
- Updated blueprint hooks.json paths
- Removed root hooks/ directory
- Updated .gitignore

## Core Skills Deepened

### interface-design
- Added Blueprint-Instance Pattern section with real hooks example

### user-experience
- Added CLI bridge pattern section
- Added User Delivery vs Development Completion section

### documentation-guide
- Added complementary relationship with user-experience skill
- Added real development experience as documentation section

### report-conventions (NEW)
- Full skill for development report conventions
- Naming: YYYY-MM-DD_topic-slug.md
- Scoping: root, namespaced, tool-specific
- CLI integration via logic/_/dev/report.py
- Integration with BRAIN, USERINPUT, TEX

## TEX Tool Created

New tool for report compilation (Markdown -> PDF):
- Uses fpdf2 (pure Python, no system deps)
- Commands: compile, list, template
- Handles headings, paragraphs, code blocks, tables, lists
- Unicode -> ASCII fallback for non-Latin characters
- Output to report/pdf/

## Report System Normalized

- Renamed undated reports with YYYY-MM-DD prefix
- Created report/README.md
- Added report/pdf/ to .gitignore
- Fixed logic/_/dev/report.py scope resolution (_ROOT was wrong, added intelligent scope resolution)

## Other Cleanup

- Removed orphaned .tests_cache.json from all tool test/ directories
- Created data/_/test/ for future test framework caches
- Cleaned OPENCLAW references from USERINPUT config and IDE prompts

## Files Modified (key)

- logic/_/hooks/IDE/Cursor/*.py (moved from hooks/instance/IDE/Cursor/)
- .cursor/hooks.json, logic/_/setup/IDE/cursor/hooks/hooks.json
- tool/USERINPUT/logic/prompts.py (new)
- logic/_/setup/IDE/cursor/prompts.py (new)
- logic/_/dev/resource.py (new, extracted from engine.py)
- logic/_/dev/report.py (fixed scope resolution)
- tool/TEX/ (new tool)
- skills/_/report-conventions/ (new skill)
- skills/_/interface-design/SKILL.md, skills/_/documentation-guide/SKILL.md, skills/_/user-experience/SKILL.md (deepened)
- .cursor/rules/userinput-invocation.mdc, userinput-timeout.mdc (strengthened)
