"""Zhipu GLM-4-Flash context pipeline.

Handles the known GLM-4-Flash quirk where multi-turn conversations
with tool_call history cause the model to return empty responses
(200+ completion tokens, empty content, no tool_calls, finish_reason=stop).

Solution: On Turn 2+, flatten prior tool_call exchanges into natural
language summaries so the model sees a clean context.

Known Issues (2026-03):
    GLM-4-Flash returns empty content+tool_calls when prior assistant
    messages contain tool_calls format. The model generates internal
    tokens (visible in usage.completion_tokens) but the output fields
    are empty. This is a model-level bug, not an API issue.
"""
import json
from typing import Any, Dict, List, Optional

from tool.LLM.logic.pipeline import ContextPipeline


class ZhipuContextPipeline(ContextPipeline):
    """Pipeline for Zhipu GLM-4-Flash.

    Applies tool history flattening for multi-turn conversations
    and validates responses for the known empty-response bug.
    """

    def prepare_messages(
        self,
        messages: List[Dict[str, Any]],
        turn_number: int = 1,
    ) -> List[Dict[str, Any]]:
        if turn_number <= 1:
            return messages
        return self._flatten_tool_history(messages)

    def validate_response(
        self,
        text: str,
        tool_calls: List[Dict[str, Any]],
        finish_reason: str = "",
        usage: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not text and not tool_calls and finish_reason == "stop":
            completion_tokens = (usage or {}).get("completion_tokens", 0)
            if completion_tokens > 0:
                return {
                    "valid": False,
                    "retry": True,
                    "reason": (
                        f"GLM-4-Flash empty response bug: generated "
                        f"{completion_tokens} tokens but content is empty. "
                        f"Retrying with flattened context."),
                    "text": text,
                    "tool_calls": tool_calls,
                }
        return {
            "valid": True,
            "retry": False,
            "text": text,
            "tool_calls": tool_calls,
        }

    def get_max_retries(self) -> int:
        return 3

    @staticmethod
    def _flatten_tool_history(
        messages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Replace tool_call exchanges with natural language summaries.

        Keeps: system prompt, summary of prior work, current turn messages.
        Strips: all assistant.tool_calls and tool-role messages.
        """
        last_user_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                last_user_idx = i
                break

        if last_user_idx <= 1:
            return messages

        system_msg = None
        if messages[0].get("role") == "system":
            system_msg = messages[0]

        summary_parts = []
        pending_reads = {}
        for m in messages[1:last_user_idx]:
            role = m.get("role", "")
            content = m.get("content") or ""
            if role == "user" and content:
                summary_parts.append(f"User asked: {content[:150]}")
            elif role == "assistant":
                if content:
                    summary_parts.append(content[:200])
                if m.get("tool_calls"):
                    for tc in m["tool_calls"]:
                        fn = tc.get("function", {})
                        name = fn.get("name", "?")
                        tc_id = tc.get("id", "")
                        try:
                            args = json.loads(fn.get("arguments", "{}"))
                        except (ValueError, TypeError):
                            args = {}
                        if name == "write_file":
                            summary_parts.append(
                                f"Wrote file: {args.get('path', '?')}")
                        elif name == "exec":
                            summary_parts.append(
                                f"Ran command: {args.get('command', '?')[:80]}")
                        elif name == "read_file":
                            path = args.get("path", "?")
                            summary_parts.append(f"Read file: {path}")
                            pending_reads[tc_id] = path
                        else:
                            summary_parts.append(f"Used tool: {name}")
            elif role == "tool":
                tc_id = m.get("tool_call_id", "")
                if tc_id in pending_reads and content:
                    path = pending_reads.pop(tc_id)
                    summary_parts.append(
                        f"[Content of {path}]\n{content[:3000]}")
                elif content:
                    summary_parts.append(f"Output: {content[:200]}")

        result = []
        if system_msg:
            result.append(system_msg)

        if summary_parts:
            summary = "\n".join(summary_parts)
            result.append({
                "role": "user",
                "content": (
                    f"Here is what was done so far:\n{summary}\n\n"
                    f"Please continue with the next request."),
            })
            result.append({
                "role": "assistant",
                "content": (
                    "Understood. I'll continue working on the task. "
                    "What would you like me to do next?"),
            })

        for m in messages[last_user_idx:]:
            result.append(m)

        return result
