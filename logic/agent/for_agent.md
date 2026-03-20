# logic/agent/ — Agent Infrastructure

Shared agent logic for conversation management, brain integration, and command execution.

## Key Files

| File | Purpose |
|------|---------|
| `brain.py` | Brain-related agent commands (read/write context, tasks) |
| `brain_tasks.py` | Task management helpers (add, done, list, progress) |
| `command.py` | Agent command parser and dispatcher |
| `ecosystem.py` | Builds ecosystem context (guidelines, skills, behaviors) for injection |
| `_json_repair.py` | Repairs malformed JSON from LLM outputs |

## Usage

These modules are consumed by `tool/LLM/logic/task/agent/conversation.py` (the agent loop) and by `hooks/instance/AI-IDE/Cursor/brain_inject.py` (context injection).

## Interface

Agent behaviors and guidelines are exposed via `logic/agent/ecosystem.py::build_ecosystem_info()`. This is the single entry point for getting the full ecosystem context to inject into an agent's prompt.
