"""Guardrail enforcement for OPENCLAW agent pipelines.

Goes beyond sandbox command filtering to enforce structural safety:
- Token budget limits per pipeline run
- Loop detection with automatic correction
- Output validation (empty, nonsensical, repeated)
- Escalation tracking for sensitive operations
"""
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GuardrailState:
    """Tracks guardrail metrics across a single pipeline run."""
    total_tokens: int = 0
    total_commands: int = 0
    total_steps: int = 0
    failed_commands: int = 0
    start_time: float = field(default_factory=time.time)
    last_response: str = ""
    repeat_count: int = 0
    writes: List[str] = field(default_factory=list)


class PipelineGuardrails:
    """Enforces safety invariants during agent pipeline execution.

    Parameters:
        max_tokens: Maximum total tokens allowed per pipeline run.
        max_steps: Maximum LLM round-trips per pipeline run.
        max_commands: Maximum total commands executed per pipeline run.
        max_duration_s: Maximum wall-clock time per pipeline run.
        max_repeats: Number of identical consecutive responses before intervention.
    """

    def __init__(self,
                 max_tokens: int = 200_000,
                 max_steps: int = 50,
                 max_commands: int = 100,
                 max_duration_s: int = 600,
                 max_repeats: int = 3):
        self.max_tokens = max_tokens
        self.max_steps = max_steps
        self.max_commands = max_commands
        self.max_duration_s = max_duration_s
        self.max_repeats = max_repeats
        self.state = GuardrailState()

    def reset(self):
        self.state = GuardrailState()

    def check_token_budget(self, tokens_used: int) -> Optional[str]:
        """Record token usage and return an error string if budget exceeded."""
        self.state.total_tokens += tokens_used
        if self.state.total_tokens > self.max_tokens:
            return (f"Token budget exceeded ({self.state.total_tokens:,}"
                    f" / {self.max_tokens:,}). Stopping pipeline.")
        return None

    def check_step_limit(self) -> Optional[str]:
        """Increment step counter and return error if limit reached."""
        self.state.total_steps += 1
        if self.state.total_steps > self.max_steps:
            return (f"Step limit reached ({self.state.total_steps}"
                    f" / {self.max_steps}). Stopping pipeline.")
        return None

    def check_command_limit(self, count: int = 1) -> Optional[str]:
        """Record command executions and return error if limit reached."""
        self.state.total_commands += count
        if self.state.total_commands > self.max_commands:
            return (f"Command limit reached ({self.state.total_commands}"
                    f" / {self.max_commands}). Stopping pipeline.")
        return None

    def check_duration(self) -> Optional[str]:
        """Return error if pipeline has been running too long."""
        elapsed = time.time() - self.state.start_time
        if elapsed > self.max_duration_s:
            return (f"Duration limit reached ({elapsed:.0f}s"
                    f" / {self.max_duration_s}s). Stopping pipeline.")
        return None

    def check_loop(self, response_text: str) -> Optional[str]:
        """Detect repeated identical responses. Returns correction message
        to inject, or None if not looping."""
        if response_text == self.state.last_response:
            self.state.repeat_count += 1
        else:
            self.state.repeat_count = 0
        self.state.last_response = response_text

        if self.state.repeat_count >= self.max_repeats:
            self.state.repeat_count = 0
            return (
                "IMPORTANT: You are repeating yourself. "
                "Try a COMPLETELY DIFFERENT approach. "
                "Use --openclaw-tool-help to discover available tools. "
                "If a command keeps failing, try an alternative."
            )
        return None

    def validate_response(self, response_text: str) -> Optional[str]:
        """Validate agent response quality. Returns error string if invalid."""
        if not response_text or not response_text.strip():
            return "Empty response from agent."
        if len(response_text.strip()) < 5:
            return f"Response too short ({len(response_text.strip())} chars)."
        return None

    def record_command_failure(self):
        """Track a failed command execution."""
        self.state.failed_commands += 1

    def record_write(self, path: str):
        """Track a file write operation for auditing."""
        self.state.writes.append(path)

    def get_summary(self) -> dict:
        """Return a summary of guardrail metrics for the current run."""
        elapsed = time.time() - self.state.start_time
        return {
            "total_tokens": self.state.total_tokens,
            "total_steps": self.state.total_steps,
            "total_commands": self.state.total_commands,
            "failed_commands": self.state.failed_commands,
            "duration_s": round(elapsed, 1),
            "writes": self.state.writes,
        }
