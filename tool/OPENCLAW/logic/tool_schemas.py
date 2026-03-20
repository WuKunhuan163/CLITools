"""Structured tool call schemas for OPENCLAW agent protocol.

Defines OpenAI-compatible function schemas for each OPENCLAW tool.
When a provider supports the ``tools`` parameter, these schemas are
sent alongside messages so the LLM returns structured JSON tool calls
instead of text-based ``<<EXEC: ...>>`` tokens.

Providers that don't support structured tool calling fall back to
the text-based protocol defined in ``protocol.py``.
"""
from typing import List, Dict, Any

TOOL_EXEC = {
    "type": "function",
    "function": {
        "name": "exec",
        "description": (
            "Execute a shell command in the project sandbox. "
            "Use for running scripts, installing packages, file operations, "
            "or any terminal command. The command runs in a sandboxed "
            "environment with the project root as working directory."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
            },
            "required": ["command"],
        },
    },
}

TOOL_READ = {
    "type": "function",
    "function": {
        "name": "read",
        "description": (
            "Read the contents of a file. Use to inspect source code, "
            "configuration files, logs, or any text file in the project."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or project-relative file path.",
                },
                "start_line": {
                    "type": "integer",
                    "description": "First line to read (1-indexed). Omit for full file.",
                },
                "end_line": {
                    "type": "integer",
                    "description": "Last line to read (inclusive). Omit for full file.",
                },
            },
            "required": ["path"],
        },
    },
}

TOOL_GREP = {
    "type": "function",
    "function": {
        "name": "grep",
        "description": (
            "Search for a pattern in files. Supports regex. "
            "Returns matching lines with file paths and line numbers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for.",
                },
                "path": {
                    "type": "string",
                    "description": (
                        "File or directory to search in. "
                        "Defaults to project root."
                    ),
                },
                "include": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g. '*.py').",
                },
            },
            "required": ["pattern"],
        },
    },
}

TOOL_SEARCH = {
    "type": "function",
    "function": {
        "name": "search",
        "description": (
            "Semantic search across the project codebase. "
            "Finds code by meaning rather than exact text matching. "
            "Use when you need to understand how something works."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query describing what to find.",
                },
                "scope": {
                    "type": "string",
                    "description": "Directory path to limit search scope.",
                },
            },
            "required": ["query"],
        },
    },
}

TOOL_TODO = {
    "type": "function",
    "function": {
        "name": "todo",
        "description": (
            "Manage the task list. Create, update, or complete tasks. "
            "Each task has an id, content, and status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "update", "complete", "list"],
                    "description": "Action to perform on the task list.",
                },
                "id": {
                    "type": "string",
                    "description": "Task ID (required for update/complete).",
                },
                "content": {
                    "type": "string",
                    "description": "Task description (required for add/update).",
                },
            },
            "required": ["action"],
        },
    },
}

TOOL_EXPERIENCE = {
    "type": "function",
    "function": {
        "name": "experience",
        "description": (
            "Record a lesson learned during this session. "
            "Lessons are stored persistently and influence future behavior. "
            "Use after fixing bugs, discovering patterns, or learning new approaches."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lesson": {
                    "type": "string",
                    "description": "The lesson or insight to record.",
                },
                "severity": {
                    "type": "string",
                    "enum": ["info", "warning", "critical"],
                    "description": "Severity level. Default: info.",
                },
                "tool": {
                    "type": "string",
                    "description": "Related tool name, if applicable.",
                },
            },
            "required": ["lesson"],
        },
    },
}

# Ordered list of all tool schemas
ALL_TOOLS: List[Dict[str, Any]] = [
    TOOL_EXEC,
    TOOL_READ,
    TOOL_GREP,
    TOOL_SEARCH,
    TOOL_TODO,
    TOOL_EXPERIENCE,
]

BLOCKING_TOOL_NAMES = {"exec", "read", "grep", "search", "todo"}
NON_BLOCKING_TOOL_NAMES = {"experience"}


def get_tool_schemas(blocking_only: bool = False) -> List[Dict[str, Any]]:
    """Return tool schemas suitable for the ``tools`` API parameter.

    Args:
        blocking_only: If True, only return schemas for blocking tools.
    """
    if blocking_only:
        return [t for t in ALL_TOOLS
                if t["function"]["name"] in BLOCKING_TOOL_NAMES]
    return list(ALL_TOOLS)
