"""Core agent loop — prompt → LLM → tools → feedback → repeat.

This is the engine that drives autonomous agent behavior. It accepts
a user prompt, sends it to an LLM provider, executes tool calls,
and iterates until the agent is done or hits limits.
"""
import json
import time
from typing import Any, Callable, Dict, List, Optional

from logic.agent.state import AgentSession
from logic.agent.context import build_context
from logic.agent.tools import BUILTIN_TOOL_DEFS, ToolHandlers, get_tool_defs_for_mode
from logic.agent.nudge import should_nudge, build_nudge_message, build_quality_nudge, build_verify_nudge


class AgentLoop:
    """Runs one agent turn: user message → LLM → tool calls → response."""

    def __init__(self,
                 session: AgentSession,
                 provider_name: str,
                 system_prompt: str = "",
                 project_root: str = "",
                 emit: Optional[Callable] = None,
                 brain=None,
                 tier: int = 1,
                 mode: str = "agent"):
        self._session = session
        self._provider_name = provider_name
        self._system_prompt = system_prompt
        self._project_root = project_root
        self._emit = emit or (lambda evt: None)
        self._brain = brain
        self._tier = tier
        self._mode = mode

        self._tool_handlers = ToolHandlers(
            cwd=session.codebase_root,
            project_root=project_root,
            env=session.environment,
            emit=self._emit,
            mode=mode,
        )

        if tier >= 2 and project_root and mode in ("agent", "meta-agent"):
            try:
                from logic.agent.memory import MemoryHandlers, MEMORY_TOOL_DEFS
                brain_type = getattr(session, "brain_type", "default") or "default"
                mh = MemoryHandlers(project_root, brain_type)
                self._tool_handlers.register("write_memory", mh.handle_write_memory)
                self._tool_handlers.register("write_daily", mh.handle_write_daily)
                self._tool_handlers.register("recall_memory", mh.handle_recall_memory)
                self._tool_handlers.register("reorganize_memory", mh.handle_reorganize_memory)
                self._memory_tool_defs = MEMORY_TOOL_DEFS
            except Exception:
                self._memory_tool_defs = []
        else:
            self._memory_tool_defs = []

        self._context_messages: List[Dict[str, Any]] = []
        if system_prompt:
            self._context_messages.append({"role": "system", "content": system_prompt})

    def register_tool(self, name: str, handler: Callable):
        """Register a custom tool handler."""
        self._tool_handlers.register(name, handler)

    def run_turn(self, text: str,
                 context_feed: Optional[Dict[str, Any]] = None,
                 max_rounds: int = 15) -> str:
        """Run one full agent turn.

        Returns the final assistant text response.
        """
        self._session.status = "running"
        self._session.message_count += 1
        self._tool_handlers.reset_turn()
        self._emit({"type": "session_status", "id": self._session.id, "status": "running"})
        self._emit({"type": "user", "text": text})

        packaged = build_context(
            self._session, text, tier=self._tier, context_feed=context_feed,
            project_root=self._project_root)
        self._context_messages.append({"role": "user", "content": packaged})

        try:
            from tool.LLM.logic.registry import get_provider, get_pipeline
            provider = get_provider(self._provider_name)
            pipeline = get_pipeline(self._provider_name)

            if not provider.is_available():
                msg = f"Provider {self._provider_name} not available."
                self._emit({"type": "text", "tokens": msg})
                self._emit({"type": "complete"})
                self._session.status = "error"
                return msg

            tools = get_tool_defs_for_mode(self._mode) + self._memory_tool_defs
            round_num = 0
            consecutive_empty = 0
            MAX_CONSECUTIVE_EMPTY = 3
            full_text = ""

            flushed_this_turn = False

            while round_num < max_rounds:
                round_num += 1
                full_text = ""
                tool_calls_accum = []

                if (self._tier >= 2 and self._mode == "agent"
                        and not flushed_this_turn and len(self._context_messages) > 10):
                    try:
                        from logic.agent.memory import should_flush_memory
                        ctx_chars = sum(len(str(m.get("content", "")))
                                        for m in self._context_messages)
                        est_tokens = ctx_chars // 4
                        max_ctx = getattr(provider.capabilities, "max_context_tokens", 128000)
                        if should_flush_memory(est_tokens, max_ctx):
                            from logic.agent.memory import FLUSH_PROMPT_EN
                            self._context_messages.append(
                                {"role": "user", "content": FLUSH_PROMPT_EN})
                            self._emit({"type": "text",
                                        "tokens": "[Memory flush triggered...]\n"})
                            flushed_this_turn = True
                    except Exception:
                        pass

                self._emit({"type": "llm_request", "provider": self._provider_name,
                             "round": round_num})

                api_messages = pipeline.prepare_messages(
                    list(self._context_messages),
                    turn_number=self._session.message_count)
                api_tools = pipeline.prepare_tools(tools, provider.capabilities)

                t0 = time.time()
                full_text, tool_calls_accum, latency = self._stream_round(
                    provider, api_messages, api_tools, round_num, t0)

                if full_text is None:
                    break

                if full_text or tool_calls_accum:
                    consecutive_empty = 0

                if not tool_calls_accum:
                    if full_text:
                        self._context_messages.append(
                            {"role": "assistant", "content": full_text})

                        if self._mode in ("ask", "plan"):
                            break

                        if self._tier >= 2 and round_num <= 6 and should_nudge(full_text):
                            has_read = any(
                                r.get("cmd", "").startswith("read:")
                                for r in self._session.environment.last_results)
                            nudge = build_nudge_message(has_read)
                            self._context_messages.append({"role": "user", "content": nudge})
                            self._emit({"type": "text", "tokens": "[Nudging agent...]\n"})
                            continue

                        if self._tier >= 2:
                            qw = build_quality_nudge(self._tool_handlers.unfixed_quality_warnings)
                            if qw and round_num <= 12:
                                self._context_messages.append({"role": "user", "content": qw})
                                self._emit({"type": "text", "tokens": "[Fixing quality...]\n"})
                                continue

                            vn = build_verify_nudge(self._tool_handlers.unverified_writes)
                            if vn and round_num <= 12 and self._session.message_count >= 2:
                                self._context_messages.append({"role": "user", "content": vn})
                                self._emit({"type": "text", "tokens": "[Verifying...]\n"})
                                continue

                    elif not full_text and tools:
                        consecutive_empty += 1
                        if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
                            self._emit({"type": "text",
                                        "tokens": f"[{consecutive_empty} consecutive empty responses — stopping.]\n"})
                            break
                        task_reminder = ""
                        if self._session.initial_prompt:
                            task_reminder = (
                                f"\n\nOriginal task: {self._session.initial_prompt[:400]}")
                        self._context_messages.append(
                            {"role": "assistant", "content": "Let me take action now."})
                        self._context_messages.append(
                            {"role": "user", "content":
                             "Your previous response was empty. Use tools to take action NOW. "
                             "Do NOT repeat file reads you already completed. "
                             "Do NOT run ls. Proceed directly with the modifications."
                             + task_reminder})
                        self._emit({"type": "text", "tokens": "[Empty response, retrying...]\n"})
                        continue

                    break

                assistant_msg = {
                    "role": "assistant",
                    "content": full_text or None,
                    "tool_calls": tool_calls_accum,
                }
                self._context_messages.append(assistant_msg)

                for tc in tool_calls_accum:
                    tc_result = self._execute_tool_call(tc)
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": tc_result.get("output", ""),
                    }
                    self._context_messages.append(tool_msg)

            self._emit({"type": "complete"})

        except Exception as e:
            self._emit({"type": "text", "tokens": f"Exception: {e}"})
            self._emit({"type": "complete"})
            full_text = f"Error: {e}"

        self._session.status = "done"
        self._emit({"type": "session_status", "id": self._session.id, "status": "done"})
        return full_text

    # Tools whose content can be streamed progressively to the frontend
    _STREAMABLE_TOOLS = {"write_file", "edit_file", "edit", "think"}

    def _stream_round(self, provider, messages, tools, round_num, t0):
        """Stream one LLM round, emitting incremental events.

        Uses send_streaming() for raw per-token deltas, enabling
        progressive rendering of tool call arguments (edit content,
        think blocks) in the frontend.

        Returns (full_text, tool_calls, latency) or (None, [], 0) on error.
        """
        full_text_parts = []
        tool_calls_by_idx: Dict[int, Dict] = {}
        streaming_tools: Dict[int, str] = {}
        error_text = None
        api_usage = {}

        try:
            for chunk in provider.send_streaming(
                    messages, temperature=0.7, max_tokens=4096, tools=tools):
                if not chunk.get("ok"):
                    error_text = chunk.get("error", "Unknown error")
                    break

                if chunk.get("usage"):
                    api_usage = chunk["usage"]

                tc_list = chunk.get("tool_calls")
                if tc_list:
                    for delta in tc_list:
                        idx = delta.get("index", 0)
                        if idx not in tool_calls_by_idx:
                            tool_calls_by_idx[idx] = {
                                "id": delta.get("id", ""),
                                "type": delta.get("type", "function"),
                                "function": {
                                    "name": delta.get("function", {}).get("name", ""),
                                    "arguments": delta.get("function", {}).get("arguments", ""),
                                },
                            }
                            fn_name = delta.get("function", {}).get("name", "")
                            if fn_name and fn_name in self._STREAMABLE_TOOLS:
                                streaming_tools[idx] = fn_name
                                self._emit({"type": "tool_stream_start",
                                            "index": idx, "name": fn_name,
                                            "round": round_num})
                                first_args = delta.get("function", {}).get("arguments", "")
                                if first_args:
                                    self._emit({"type": "tool_stream_delta",
                                                "index": idx,
                                                "content": first_args})
                        else:
                            existing = tool_calls_by_idx[idx]
                            if delta.get("id"):
                                existing["id"] = delta["id"]
                            fn_delta = delta.get("function", {})
                            if fn_delta.get("name"):
                                existing["function"]["name"] = fn_delta["name"]
                                if (fn_delta["name"] in self._STREAMABLE_TOOLS
                                        and idx not in streaming_tools):
                                    streaming_tools[idx] = fn_delta["name"]
                                    self._emit({"type": "tool_stream_start",
                                                "index": idx,
                                                "name": fn_delta["name"],
                                                "round": round_num})
                            if fn_delta.get("arguments"):
                                existing["function"]["arguments"] += fn_delta["arguments"]
                                if idx in streaming_tools:
                                    self._emit({"type": "tool_stream_delta",
                                                "index": idx,
                                                "content": fn_delta["arguments"]})
                    continue

                text = chunk.get("text", "")
                if text:
                    full_text_parts.append(text)
                    self._emit({"type": "text", "tokens": text})

                reasoning = chunk.get("reasoning", "")
                if reasoning:
                    self._emit({"type": "thinking", "tokens": reasoning})
        except Exception as e:
            error_text = str(e)

        latency = time.time() - t0

        for idx in streaming_tools:
            self._emit({"type": "tool_stream_end", "index": idx, "round": round_num})

        if error_text:
            self._emit({"type": "text", "tokens": f"Error: {error_text}"})
            return None, [], latency

        full_text = "".join(full_text_parts)
        merged_tc = [tool_calls_by_idx[k] for k in sorted(tool_calls_by_idx)]

        try:
            from tool.LLM.logic.usage import record_usage
            model = getattr(provider, "_model", provider.name)
            api_key = getattr(provider, "_api_key", "")
            record_usage(provider.name, model,
                         {"ok": True, "text": full_text, "usage": api_usage},
                         latency, api_key=api_key)
        except Exception:
            pass

        self._emit({"type": "llm_response_end", "round": round_num,
                     "latency_s": round(latency, 3),
                     "has_tool_calls": bool(merged_tc),
                     "_full_text": full_text})

        return full_text, merged_tc, latency

    def _execute_tool_call(self, tool_call: dict) -> dict:
        func = tool_call.get("function", {})
        name = func.get("name", "")
        raw_args = func.get("arguments", "{}")
        args = self._parse_tool_args(raw_args)
        handler = self._tool_handlers.get(name)
        if handler:
            return handler(args)
        self._emit({"type": "text", "tokens": f"Unknown tool: {name}"})
        return {"ok": False, "output": f"Unknown tool: {name}"}

    @staticmethod
    def _parse_tool_args(raw: str) -> dict:
        """Enterprise-grade JSON parser with multi-layer repair for LLM outputs.

        Layer 1: Direct json.loads
        Layer 2: Structural repair (strip special tokens, fix common issues)
        Layer 3: Regex key-value extraction (last resort)
        """
        from logic.agent._json_repair import repair_and_parse
        return repair_and_parse(raw)
