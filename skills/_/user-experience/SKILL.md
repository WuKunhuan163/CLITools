---
name: user-experience
description: Separating user experience from code logic. Covers developer-accessible directory placement, user-facing delivery, contribution-friendly design, and the distinction between what users see vs what developers maintain.
---

# User Experience & Delivery

Software exists for users. Code quality, modularization, and interface design are means — the end is delivering something a user can see, use, and want to contribute to. This skill defines the boundary between "user experience" and "code logic," and how development should serve both.

## The Two Layers

| Layer | Purpose | Example |
|-------|---------|---------|
| **User Experience** | What users see, feel, access | Root `test/` directory, CLI output, web GUI, README.md |
| **Code Logic** | How developers organize internals | `logic/`, `interface/`, `data/_/`, cache files |

These must be consciously separated. Mixing them creates confusion: users stumble over internal cache files, developers can't find user-facing assets, and agents don't know what to prioritize.

## Directory Placement: Accessibility vs Organization

### Principle: Frequently-Accessed Developer Artifacts Go at Root Level

Developers write tests regularly. Tests should be easy to find, easy to add, easy to run. That's why `test/` is a root-level symmetric directory — visible the moment you `ls` the project.

But `test/.tests_cache.json` is a machine-generated cache. Developers don't read it, don't edit it, don't even know it exists. It belongs in `data/_/test/` — the canonical location for internal data that supports developer workflows but isn't developer-written content.

### Decision Matrix

| Content Type | Location | Rationale |
|-------------|----------|-----------|
| User writes/reads regularly | Root level (e.g., `test/`, `skills/`) | Accessibility — minimize navigation depth |
| Machine-generated cache/state | `data/_/<module>/` | Hidden from users, organized by function |
| User-facing documentation | Alongside the code it documents | README.md in each directory |
| API keys, secrets, configs | `data/` (gitignored) | Security + isolation |
| Large binary assets | Remote `tool` branch, lazy-fetched | Don't bloat user downloads |

## Delivery Awareness

When an agent develops something — a web frontend, a CLI feature, a configuration wizard — the work isn't done when the code compiles. It's done when the user can experience it.

### The Delivery Checklist

After implementing a user-facing feature:

1. **Can the user find it?** — Is there a CLI command, menu entry, or documentation pointing to it?
2. **Can the user start it?** — If it's a web app, offer to launch the server and open the browser. If it's a CLI command, show the exact invocation.
3. **Can the user tell it's working?** — Provide visual feedback: a status message, a loaded page, a success confirmation.
4. **Can the user report problems?** — Is there a debug endpoint, log file, or error message that helps diagnose issues?

### Real Lesson: The Frontend Monolith

An agent built an elaborate HTML assistant GUI — hundreds of lines of JavaScript, CSS, real-time SSE integration. It reported success after code compilation. But the frontend was actually broken: stale CSS caches, JavaScript errors in the console, unconnected event handlers. Nobody noticed because:

- No debug endpoint existed to verify frontend state
- No automated smoke test checked if the page actually rendered
- The agent never opened the browser to look at what it built

**Fix**: When developing frontends, always design a debug/health endpoint alongside the UI. Open the result in a browser before declaring success.

## User Contribution Design

A healthy project invites contributions. This means:

### Make the Structure Self-Explanatory

A new contributor running `ls` should understand the project layout within 30 seconds:
- `tool/` — clearly contains tools
- `test/` — clearly contains tests
- `skills/` — clearly contains development guides
- `README.md` — clearly explains the project

### Hide Complexity, Reveal Capability

Internal directories (`logic/_/`, `data/_/`, `hooks/instance/`) should be invisible to casual browsing but well-documented for those who dig deeper. The root-level directories present the "capability surface" — what the project can do.

### Symmetric Design Reduces Learning Curve

When every tool has the same structure (`main.py`, `logic/`, `interface/`, `test/`), a contributor who understands one tool understands all of them. This is the user-experience benefit of symmetric design — predictability reduces cognitive load.

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Cache files in user-visible directories | Clutter, confusion | Move to `data/_/<module>/` |
| Features with no discovery path | Users never find them | Add CLI entry point + docs |
| Developing without opening the result | Silent failures | Test user-facing features visually |
| Complex root-level directory structure | Intimidating to contributors | Keep root clean, push internals down |
| Mixing user content with machine content | Hard to gitignore correctly | Separate data/ from user-editable content |
| Building frontend without debug endpoints | Impossible to diagnose issues | Add `/debug/status` alongside new UIs |
