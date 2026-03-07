"""OpenClawCore — canonical shared state for all OPENCLAW GUIs.

Both CLI and HTML GUIs wrap this core. It owns:
  - SessionManager (sessions, messages, logs)
  - Active LLM provider
  - Agent context (SessionContext per active session)
  - Agent environment (AgentEnvironment)
  - Compression settings
  - Guardrails

The core is GUI-agnostic: no terminal codes, no browser references.
GUIs call core methods and render the results in their own way.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from tool.OPENCLAW.logic.session import SessionManager, Session
from tool.OPENCLAW.logic.sandbox import execute_command, get_project_summary
from tool.OPENCLAW.logic.protocol import (
    build_system_prompt, build_task_message, build_feedback_message,
    parse_response_segments,
)
from tool.OPENCLAW.logic.skills import build_skill_hint

MAX_ITERATIONS = 50


class StepResult:
    """Result of executing one agent step."""

    __slots__ = (
        "step_summary", "segments", "task_complete", "step_complete",
        "title", "response_text", "tokens_used", "latency_s",
    )

    def __init__(self):
        self.step_summary: Optional[str] = None
        self.segments: list = []
        self.task_complete: bool = False
        self.step_complete: bool = False
        self.title: Optional[str] = None
        self.response_text: str = ""
        self.tokens_used: int = 0
        self.latency_s: float = 0.0


class CommandResult:
    """Result of executing a single command."""

    __slots__ = ("cmd", "ok", "exit_code", "output", "error")

    def __init__(self, cmd: str, raw: Dict[str, Any]):
        self.cmd = cmd
        self.ok: bool = raw.get("ok", False)
        self.exit_code: int = raw.get("exit_code", -1)
        self.output: str = raw.get("output", "")
        self.error: str = raw.get("error", "")


class OpenClawCore:
    """GUI-agnostic OPENCLAW engine.

    Parameters
    ----------
    data_dir : Path
        Data directory (contains sessions/, config, etc.).
    backend : str
        LLM provider name.
    log_limit : int
        Max logs per session before rotation.
    compression_trigger : float
        Context ratio that triggers compression (0-1).
    compression_target : float
        Target compression ratio (0-1).
    """

    def __init__(
        self,
        data_dir: Path,
        backend: str = "nvidia-glm-4-7b",
        log_limit: int = 1024,
        compression_trigger: float = 0.5,
        compression_target: float = 0.1,
    ):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session_mgr = SessionManager(data_dir, log_limit=log_limit)
        self.backend = backend
        self.compression_trigger = compression_trigger
        self.compression_target = compression_target

        self._provider = None
        self._contexts: Dict[str, Any] = {}  # session_id -> SessionContext
        self._active_session_id: Optional[str] = None
        self._iteration: int = 0

    @property
    def active_session(self) -> Optional[Session]:
        if self._active_session_id:
            return self.session_mgr.get_session(self._active_session_id)
        return None

    def init_provider(self):
        """Initialize or reinitialize the LLM provider."""
        from tool.LLM.logic.registry import get_provider
        self._provider = get_provider(self.backend)

    @property
    def provider(self):
        return self._provider

    @property
    def provider_ready(self) -> bool:
        return self._provider is not None and self._provider.is_available()

    def set_backend(self, name: str):
        """Switch the active LLM backend."""
        from tool.LLM.logic.config import set_config_value
        self.backend = name
        set_config_value("active_backend", name)
        self.init_provider()

    def create_session(self, title: str = "") -> Session:
        session = self.session_mgr.create_session(title)
        self._active_session_id = session.id
        self._iteration = 0
        return session

    def switch_session(self, session_id: str) -> Optional[Session]:
        s = self.session_mgr.get_session(session_id)
        if s:
            self._active_session_id = s.id
            self._iteration = 0
            self._contexts.pop(session_id, None)
        return s

    def get_context(self, session_id: str):
        """Get or create a SessionContext for a session."""
        if session_id not in self._contexts:
            from tool.LLM.logic.session_context import SessionContext
            project_summary = get_project_summary()
            system_prompt = build_system_prompt(project_summary)
            self._contexts[session_id] = SessionContext(
                system_prompt=system_prompt,
                max_context_tokens=32000,
            )
        return self._contexts[session_id]

    def clear_context(self, session_id: str):
        self._contexts.pop(session_id, None)

    def send_task(self, session_id: str, user_task: str) -> StepResult:
        """Send a user task to the agent and get the first response.

        This is a blocking call. For streaming, use send_task_streaming().
        Returns a StepResult with parsed segments.
        """
        session = self.session_mgr.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        self.session_mgr.add_message(session_id, "user", user_task)
        context = self.get_context(session_id)

        task_msg = build_task_message(user_task)
        context.add_user(task_msg)

        self._iteration += 1
        messages = context.get_messages_for_api()

        result = self._provider.send(
            messages, temperature=0.7, max_tokens=16384)

        step = StepResult()
        if not result.get("ok"):
            step.response_text = result.get("error", "Unknown error")
            return step

        step.response_text = result.get("text", "")
        step.tokens_used = result.get("usage", {}).get("total_tokens", 0)
        step.latency_s = result.get("latency_s", 0)

        context.add_assistant(step.response_text)

        parsed = parse_response_segments(step.response_text)
        step.segments = parsed["segments"]
        step.task_complete = parsed["task_complete"]
        step.step_complete = parsed["step_complete"]
        step.step_summary = parsed.get("step_summary")
        step.title = parsed.get("title")

        if self._iteration == 1 and step.title:
            self.session_mgr.update_title(session_id, step.title)

        if step.task_complete:
            self.session_mgr.complete_session(session_id)
            self.clear_context(session_id)
            self._iteration = 0

        return step

    def execute_commands(self, session_id: str,
                         commands: List[str]) -> List[CommandResult]:
        """Execute a list of commands from the agent and return results."""
        results = []
        for cmd in commands:
            raw = execute_command(cmd)
            cr = CommandResult(cmd, raw)
            self.session_mgr.add_message(session_id, "system", f"[Exec] {cmd}")
            results.append(cr)
        return results

    def send_feedback(self, session_id: str,
                      command_results: List[CommandResult]) -> str:
        """Build and inject feedback from command results into context."""
        context = self.get_context(session_id)
        parts = []
        for cr in command_results:
            raw = {"ok": cr.ok, "output": cr.output, "error": cr.error}
            parts.append(build_feedback_message(cr.cmd, raw))

        error_context = " ".join(
            p.split("\n")[0] for p in parts if "[Command FAILED]" in p)
        if error_context:
            hint = build_skill_hint(error_context)
            if hint:
                parts.append(hint)

        all_feedback = "\n\n".join(parts)
        all_feedback += (
            "\n\nContinue with the task. Start with <<STEP: label >>. "
            "End with <<OPENCLAW_STEP_COMPLETE>> or "
            "<<OPENCLAW_TASK_COMPLETE>> when fully done."
        )
        context.add_user(all_feedback)
        return all_feedback
