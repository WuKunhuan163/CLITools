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

        if tier >= 2 and project_root and mode == "agent":
            try:
                from logic.agent.memory import MemoryHandlers, MEMORY_TOOL_DEFS
                brain_type = getattr(session, "brain_type", "default") or "default"
                mh = MemoryHandlers(project_root, brain_type)
                self._tool_handlers.register("write_memory", mh.handle_write_memory)
                self._tool_handlers.register("write_daily", mh.handle_write_daily)
                self._tool_handlers.register("recall_memory", mh.handle_recall_memory)
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
            empty_retries = 0
            max_empty_retries = pipeline.get_max_retries()
            full_text = ""

            while round_num < max_rounds:
                round_num += 1
                full_text = ""
                tool_calls_accum = []

                self._emit({"type": "llm_request", "provider": self._provider_name,
                             "round": round_num})

                api_messages = pipeline.prepare_messages(
                    list(self._context_messages),
                    turn_number=self._session.message_count)
                api_tools = pipeline.prepare_tools(tools, provider.capabilities)

                t0 = time.time()
                result = provider.send(
                    api_messages, temperature=0.7, max_tokens=4096,
                    tools=api_tools)
                latency = time.time() - t0

                if not result.get("ok"):
                    err = result.get("error", "Unknown error")
                    self._emit({"type": "text", "tokens": f"Error: {err}"})
                    break

                full_text = result.get("text", "") or ""
                if result.get("tool_calls"):
                    tool_calls_accum = result["tool_calls"]

                self._emit({"type": "llm_response_end", "round": round_num,
                             "latency_s": round(latency, 3),
                             "has_tool_calls": bool(tool_calls_accum)})

                if full_text:
                    self._emit({"type": "text", "tokens": full_text})

                if not tool_calls_accum:
                    if full_text:
                        self._context_messages.append(
                            {"role": "assistant", "content": full_text})

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

                    elif tools and empty_retries < max_empty_retries:
                        empty_retries += 1
                        self._context_messages.append(
                            {"role": "assistant", "content": "Let me take action now."})
                        self._context_messages.append(
                            {"role": "user", "content": "Your response was empty. Use tools NOW."})
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

    def _execute_tool_call(self, tool_call: dict) -> dict:
        func = tool_call.get("function", {})
        name = func.get("name", "")
        try:
            args = json.loads(func.get("arguments", "{}"))
        except Exception:
            args = {}
        handler = self._tool_handlers.get(name)
        if handler:
            return handler(args)
        self._emit({"type": "text", "tokens": f"Unknown tool: {name}"})
        return {"ok": False, "output": f"Unknown tool: {name}"}
