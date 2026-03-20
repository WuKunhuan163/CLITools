"""API-based task execution pipeline for OPENCLAW.

Mirrors ``pipeline.py`` but uses an LLM API (GLM-4.7 via NVIDIA Build)
instead of Yuanbao browser automation.  This is the compliant alternative
that avoids CDMCP UI automation for the LLM interaction.

Architecture (from YAB-Bridge spec):
  - OpenClaw (brain): session management, context, tool dispatch
  - LLM API (GLM-4.7): decision making via OpenAI-compatible endpoint
  - Sandbox: local command execution
"""
import time
import threading
from typing import Optional, Callable

from tool.LLM.interface.main import LLMProvider
from tool.LLM.interface.main import SessionContext
from tool.OPENCLAW.logic.sandbox import execute_command, get_project_summary
from tool.OPENCLAW.logic.protocol import (
    build_system_prompt, build_task_message, build_feedback_message,
    parse_structured_tool_calls, AgentEnvironment,
)
from tool.OPENCLAW.logic.session import SessionManager, Session


MAX_ITERATIONS = 50
RESPONSE_TIMEOUT = 120


class APIPipeline:
    """Task execution pipeline using an API-based LLM provider."""

    def __init__(self, session_mgr: SessionManager, session: Session,
                 provider: LLMProvider,
                 on_message: Optional[Callable] = None,
                 on_status: Optional[Callable] = None,
                 on_title: Optional[Callable] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 16384):
        self.session_mgr = session_mgr
        self.session = session
        self.provider = provider
        self.on_message = on_message or (lambda role, text: None)
        self.on_status = on_status or (lambda text: None)
        self.on_title = on_title or (lambda title: None)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._iteration = 0
        self._context: Optional[SessionContext] = None
        self._env = AgentEnvironment()

    def start(self, user_task: str):
        """Start the pipeline in a background thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._run, args=(user_task,), daemon=True
        )
        self._thread.start()

    def stop(self):
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def _emit_message(self, role: str, content: str, **kwargs):
        self.session_mgr.add_message(self.session.id, role, content, **kwargs)
        self.on_message(role, content)

    def _emit_status(self, text: str):
        self.on_status(text)

    def _run(self, user_task: str):
        try:
            self._emit_status("Initializing API pipeline...")

            if not self.provider.is_available():
                self._emit_message("system",
                    f"LLM provider '{self.provider.name}' not available. "
                    "Run OPENCLAW setup-llm to configure.")
                self._running = False
                return

            project_summary = get_project_summary()
            system_prompt = build_system_prompt(project_summary)
            self._context = SessionContext(
                system_prompt=system_prompt,
                max_context_tokens=32000,
            )

            task_msg = build_task_message(user_task, environment=self._env)
            self._context.add_user(task_msg)
            self._emit_message("user", user_task)

            self._emit_status(f"Sending task to {self.provider.name}...")

            prev_response_text = ""
            repeat_count = 0

            while self._running and self._iteration < MAX_ITERATIONS:
                self._iteration += 1
                self._emit_status(
                    f"Waiting for response (iteration {self._iteration})...")

                result = self.provider.send(
                    self._context.get_messages_for_api(),
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                if not result.get("ok"):
                    error = result.get("error", "Unknown error")
                    self._emit_message("system", f"API error: {error}")
                    if "429" in str(error):
                        self._emit_status("Rate limited. Waiting 60s...")
                        time.sleep(60)
                        continue
                    break

                response_text = result.get("text", "")
                if not response_text:
                    self._emit_message("system", "Empty response from API.")
                    break

                self._context.add_assistant(response_text)

                if response_text == prev_response_text:
                    repeat_count += 1
                    if repeat_count >= 3:
                        self._emit_message("system",
                            "Agent stuck in loop. Injecting correction...")
                        correction = (
                            "IMPORTANT: You are repeating yourself. "
                            "Try a DIFFERENT command or approach. "
                            "Use --openclaw-tool-help to discover tools."
                        )
                        self._context.add_user(correction)
                        repeat_count = 0
                        continue
                else:
                    repeat_count = 0
                prev_response_text = response_text

                tool_calls_raw = []  # TODO: extract from API response
                parsed = parse_structured_tool_calls(
                    response_text, tool_calls_raw)

                if self._iteration == 1 and parsed.get("title"):
                    self.session_mgr.update_title(
                        self.session.id, parsed["title"])
                    self.on_title(parsed["title"])
                elif self._iteration == 1:
                    auto_title = response_text[:40].strip().split("\n")[0]
                    if auto_title:
                        self.session_mgr.update_title(
                            self.session.id, auto_title)
                        self.on_title(auto_title)

                thoughts = [s["content"] for s in parsed["segments"]
                            if s["type"] == "thought"]
                if thoughts:
                    self._emit_message("assistant", "\n".join(thoughts))

                for seg in parsed["segments"]:
                    if seg["type"] == "experience":
                        self._emit_message(
                            "system",
                            f"[Experience recorded] {seg['content']}")

                if parsed.get("complete"):
                    self._emit_message("system", "Task completed by agent.")
                    self._emit_status("Task completed.")
                    self.session_mgr.complete_session(self.session.id)
                    break

                commands = [s["content"] for s in parsed["segments"]
                            if s["type"] == "command"]
                if not commands:
                    self._emit_status("Response received (no commands).")
                    break

                feedback_parts = []
                for cmd in commands:
                    self._emit_status(f"Executing: {cmd}")
                    self._emit_message("system", f"[Executing] {cmd}")
                    cmd_result = execute_command(cmd)
                    feedback = build_feedback_message(cmd, cmd_result)
                    feedback_parts.append(feedback)

                    ok = cmd_result.get("ok", False)
                    output_preview = cmd_result.get(
                        "output", cmd_result.get("error", ""))
                    self._env.record_result(cmd, ok, output_preview)

                    # Auto-populate environment from exploration commands
                    if ok and "--openclaw-tool-help" in cmd:
                        tool_parts = cmd.split()
                        if len(tool_parts) >= 2:
                            t_name = tool_parts[-1]
                            desc = output_preview[:100].replace("\n", " ")
                            self._env.observe_tool(t_name, desc)
                    elif ok and "TOOL --search tools" in cmd:
                        for line in output_preview.split("\n"):
                            line = line.strip()
                            if ". " in line and "%" in line:
                                parts_l = line.split(". ", 1)
                                if len(parts_l) == 2:
                                    rest = parts_l[1]
                                    name_end = rest.find(" (")
                                    if name_end > 0:
                                        self._env.observe_tool(
                                            rest[:name_end], rest)

                    if output_preview:
                        preview = output_preview[:200]
                        if len(output_preview) > 200:
                            preview += "..."
                        self._emit_message("feedback", preview)

                all_feedback = "\n\n".join(feedback_parts)
                all_feedback += (
                    "\n\nContinue with the task. "
                    "Output your next <<EXEC: command >> or "
                    "<<OPENCLAW_TASK_COMPLETE>> when done."
                )
                self._context.add_user(all_feedback)
                self._emit_status("Sending results back to agent...")

                usage = result.get("usage", {})
                if usage:
                    total = usage.get("total_tokens", 0)
                    if total > 0:
                        self._emit_status(
                            f"Token usage: {total} "
                            f"(prompt: {usage.get('prompt_tokens', 0)}, "
                            f"completion: {usage.get('completion_tokens', 0)})")

                time.sleep(0.5)

            if self._iteration >= MAX_ITERATIONS:
                self._emit_message("system",
                    f"Reached maximum iterations ({MAX_ITERATIONS}).")
                self._emit_status("Max iterations reached.")

        except Exception as e:
            self._emit_message("system", f"Pipeline error: {e}")
            self._emit_status(f"Error: {e}")
        finally:
            self._running = False
            self._emit_status("Pipeline stopped.")
