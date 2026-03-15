"""Base context pipeline for LLM providers.

Each provider can have a custom pipeline that transforms messages,
tools, and responses to handle model-specific quirks. The default
pipeline is a pass-through.

Pipeline stages:
  1. prepare_messages(): Transform messages before sending to API
  2. prepare_tools(): Filter/transform tool schemas for the model
  3. validate_response(): Check response and decide if retry needed

Architecture:
    ConversationManager
        → pipeline.prepare_messages(messages)
        → pipeline.prepare_tools(tools, capabilities)
        → provider.stream(prepared_messages, tools=prepared_tools)
        → pipeline.validate_response(response)

Context Feed Compression:
    For multi-round agent sessions, tool outputs grow rapidly. The
    compress_history() function keeps full output for the most recent
    FULL_ROUNDS rounds and compresses older tool results to first/last
    line summaries. This bounds context growth while preserving the
    agent's ability to recall what it did.

    Compression strategy per tool type:
      - edit_file: "Edited {file}: {ok/fail}, {N} lines changed"
      - read_file: First line + "..." + last line
      - exec: "Ran '{cmd}': {ok/fail}. First: ... Last: ..."
      - search: "Searched '{pattern}': {N} results"
      - think: Full content preserved (already concise)
      - text (assistant): First + last sentence
"""
import json as _json
import re as _re
from typing import Any, Dict, List, Optional

FULL_ROUNDS = 3
_MAX_COMPRESSED_CHARS = 200


def _first_last(text: str, max_chars: int = _MAX_COMPRESSED_CHARS) -> str:
    """Return first line + ... + last line, capped at max_chars."""
    lines = text.strip().splitlines()
    if len(lines) <= 2 or len(text) <= max_chars:
        return text[:max_chars]
    first = lines[0][:max_chars // 2]
    last = lines[-1][:max_chars // 2]
    return f"{first}\n... ({len(lines)} lines) ...\n{last}"


def _compress_tool_content(content: str, tool_call: Dict[str, Any] = None) -> str:
    """Compress a tool result message for an older round."""
    if not content or len(content) <= _MAX_COMPRESSED_CHARS:
        return content

    fn_name = ""
    fn_args = {}
    if tool_call:
        for tc in tool_call.get("tool_calls", []):
            fn = tc.get("function", {})
            fn_name = fn.get("name", "")
            try:
                fn_args = _json.loads(fn.get("arguments", "{}"))
            except Exception:
                fn_args = {}
            break

    if fn_name in ("edit_file", "edit", "write_file"):
        path = fn_args.get("path", "?")
        ok = "ok" if "Written" in content or "Edited" in content else "fail"
        line_count = content.count("\n") + 1
        return f"[{ok}] Edited {path} ({line_count} lines)"

    if fn_name in ("read_file", "read"):
        path = fn_args.get("path", "?")
        return _first_last(content)

    if fn_name == "exec":
        cmd = fn_args.get("command", "?")
        cmd_short = cmd[:60] + "..." if len(cmd) > 60 else cmd
        ok = "ok" if not content.startswith("Error") else "fail"
        fl = _first_last(content, 150)
        return f"[{ok}] `{cmd_short}`\n{fl}"

    if fn_name == "search":
        pattern = fn_args.get("pattern", "?")
        match_count = content.count("\n")
        return f"Searched '{pattern}': ~{match_count} result lines"

    return _first_last(content)


def _identify_rounds(messages: List[Dict[str, Any]]) -> List[int]:
    """Return indices of user messages that start each round."""
    indices = []
    for i, msg in enumerate(messages):
        if msg.get("role") == "user":
            indices.append(i)
    return indices


def compress_history(
    messages: List[Dict[str, Any]],
    full_rounds: int = FULL_ROUNDS,
) -> List[Dict[str, Any]]:
    """Compress tool outputs in older rounds, keeping recent rounds intact.

    This is non-destructive: returns a new list with compressed content.
    The original messages are not modified.
    """
    user_indices = _identify_rounds(messages)
    if len(user_indices) <= full_rounds:
        return messages

    cutoff_idx = user_indices[-full_rounds]

    result = []
    last_assistant = None
    for i, msg in enumerate(messages):
        if i >= cutoff_idx:
            result.append(msg)
            continue

        role = msg.get("role", "")
        if role == "system":
            result.append(msg)
        elif role == "user":
            result.append(msg)
            last_assistant = None
        elif role == "assistant":
            last_assistant = msg
            if msg.get("tool_calls"):
                result.append(msg)
            elif msg.get("content"):
                text = msg["content"]
                if len(text) > _MAX_COMPRESSED_CHARS:
                    result.append({**msg, "content": _first_last(text)})
                else:
                    result.append(msg)
            else:
                result.append(msg)
        elif role == "tool":
            content = msg.get("content", "")
            if len(content) > _MAX_COMPRESSED_CHARS:
                compressed = _compress_tool_content(content, last_assistant)
                result.append({**msg, "content": compressed})
            else:
                result.append(msg)
        else:
            result.append(msg)

    return result


class ContextPipeline:
    """Base context pipeline — pass-through implementation.

    Override in provider-specific pipelines to handle model quirks.
    """

    def prepare_messages(
        self,
        messages: List[Dict[str, Any]],
        turn_number: int = 1,
    ) -> List[Dict[str, Any]]:
        """Transform messages before sending to the API.

        Applies round-based history compression by default: tool outputs
        from rounds older than the most recent FULL_ROUNDS are compressed
        to first/last line summaries. Override to customize.

        Parameters
        ----------
        messages : list
            OpenAI-format message list.
        turn_number : int
            Which user turn this is (1 = first message, 2+ = follow-up).

        Returns
        -------
        list
            Transformed messages.
        """
        return compress_history(messages)

    def prepare_tools(
        self,
        tools: Optional[List[Dict[str, Any]]],
        capabilities: Optional[Any] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Filter or transform tool schemas based on model capabilities.

        For example, remove image-related tools for non-vision models,
        or simplify complex tool schemas for weaker models.
        """
        return tools

    def validate_response(
        self,
        text: str,
        tool_calls: List[Dict[str, Any]],
        finish_reason: str = "",
        usage: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate the model's response and decide if retry is needed.

        Returns
        -------
        dict
            {
                "valid": bool,
                "retry": bool,
                "reason": str (if invalid),
                "text": str (possibly cleaned text),
                "tool_calls": list (possibly cleaned tool_calls),
            }
        """
        return {
            "valid": True,
            "retry": False,
            "text": text,
            "tool_calls": tool_calls,
        }

    def get_max_retries(self) -> int:
        """Maximum number of retries this pipeline allows for empty responses."""
        return 2
