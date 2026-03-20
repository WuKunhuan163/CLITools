"""Multi-turn session context manager for API-based LLM providers.

Maintains a ``messages`` array in memory, handling:
  - System prompt injection
  - Context truncation when approaching token limits
"""
from typing import Dict, Any, List


DEFAULT_MAX_CONTEXT_TOKENS = 32000
APPROX_CHARS_PER_TOKEN = 4


class SessionContext:
    """Manages conversation history for one session.

    The messages array is kept in OpenAI format:
        [{"role": "system"|"user"|"assistant", "content": "..."}]
    """

    def __init__(self, system_prompt: str = "",
                 max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS):
        self.system_prompt = system_prompt
        self.max_context_tokens = max_context_tokens
        self._messages: List[Dict[str, str]] = []
        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})

    @property
    def messages(self) -> List[Dict[str, str]]:
        return list(self._messages)

    def add_user(self, content: str):
        self._messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant(self, content: str):
        self._messages.append({"role": "assistant", "content": content})
        self._trim()

    def add_message(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})
        self._trim()

    def add_raw_message(self, message: Dict[str, Any]):
        """Add a pre-structured message dict (e.g. assistant with tool_calls, or tool result)."""
        self._messages.append(message)
        self._trim()

    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """Return the current messages array for sending to the API."""
        return list(self._messages)

    def _estimate_tokens(self) -> int:
        total = 0
        for m in self._messages:
            content = m.get("content") or ""
            total += len(content) // APPROX_CHARS_PER_TOKEN + 4
            if "tool_calls" in m:
                import json
                total += len(json.dumps(m["tool_calls"])) // APPROX_CHARS_PER_TOKEN
        return total

    def _trim(self):
        """Progressive context disclosure: compress old tool outputs before dropping messages.

        Strategy (inspired by claude-mem L0/L1/L2):
        1. First pass: compress tool outputs older than the freshness window to L0 summaries
        2. Second pass: if still over limit, drop oldest non-system messages (FIFO)
        """
        if self._estimate_tokens() <= self.max_context_tokens:
            return

        freshness_window = 6
        start = 1 if self._messages and self._messages[0].get("role") == "system" else 0
        compressible_end = max(start, len(self._messages) - freshness_window)

        for i in range(start, compressible_end):
            msg = self._messages[i]
            if msg.get("role") != "tool":
                continue
            content = msg.get("content", "")
            if len(content) <= 200:
                continue
            summary = self._make_l0_summary(content)
            self._messages[i] = {
                "role": "tool",
                "tool_call_id": msg.get("tool_call_id", ""),
                "content": summary,
            }

        while (self._estimate_tokens() > self.max_context_tokens
               and len(self._messages) > 2):
            if self._messages[0].get("role") == "system":
                if len(self._messages) > 2:
                    self._messages.pop(1)
                else:
                    break
            else:
                self._messages.pop(0)

    @staticmethod
    def _make_l0_summary(content: str) -> str:
        """Generate a compact L0 summary from tool output content.

        Preserves: line count, key status indicators, file paths.
        Drops: verbose content, raw data, repeated lines.
        If content already starts with [L0:...], extract and preserve that header.
        """
        if content.startswith("[L0:"):
            first_newline = content.find("\n")
            if first_newline > 0:
                return content[:first_newline].strip()
            return content.strip()[:200]

        lines = content.split("\n")
        total_lines = len(lines)
        total_chars = len(content)

        status_line = ""
        for line in lines[:5]:
            stripped = line.strip()
            if any(kw in stripped.lower() for kw in
                   ("error", "success", "fail", "exit code", "written",
                    "created", "deleted", "found", "match", "total")):
                status_line = stripped[:120]
                break

        if status_line:
            return f"[L0: {total_lines} lines, {total_chars} chars] {status_line}"
        first_line = lines[0].strip()[:100] if lines else ""
        return f"[L0: {total_lines} lines, {total_chars} chars] {first_line}"

    def needs_compression(self, trigger_ratio: float = 0.5) -> bool:
        """Check if context exceeds the trigger threshold.

        Parameters
        ----------
        trigger_ratio : float
            Fraction of max_context_tokens that triggers compression.
            Default 0.5 means compress when context hits 50% of limit.

        Returns
        -------
        bool
        """
        return self._estimate_tokens() > int(self.max_context_tokens * trigger_ratio)

    def build_compression_prompt(self, target_ratio: float = 0.1) -> str:
        """Build a prompt asking the agent to summarize its own context.

        Parameters
        ----------
        target_ratio : float
            Target size as fraction of max_context_tokens after compression.
            Default 0.1 means compress down to 10% of context limit.

        Returns
        -------
        str
            Compression instruction to send as a user message.
        """
        current_tokens = self._estimate_tokens()
        target_tokens = int(self.max_context_tokens * target_ratio)

        return (
            f"CONTEXT COMPRESSION REQUIRED.\n\n"
            f"Your context has grown to approximately {current_tokens} tokens "
            f"(limit: {self.max_context_tokens}). "
            f"Summarize the conversation so far into {target_tokens} tokens or fewer.\n\n"
            f"Rules:\n"
            f"1. Preserve the MOST RECENT actions, commands, and results.\n"
            f"2. Preserve any active task state and next steps.\n"
            f"3. Summarize older turns into brief bullet points.\n"
            f"4. Keep all discovered tool names, interface references, and lessons.\n"
            f"5. Drop verbose command outputs, keep only results.\n"
            f"6. Output ONLY the summary text, no preamble.\n\n"
            f"Begin summary:"
        )

    def apply_compression(self, summary: str):
        """Replace all non-system messages with the compressed summary.

        Parameters
        ----------
        summary : str
            The agent's compressed summary of the conversation.
        """
        system = None
        if self._messages and self._messages[0].get("role") == "system":
            system = self._messages[0]
        self._messages = []
        if system:
            self._messages.append(system)
        self._messages.append({
            "role": "user",
            "content": f"[Context Summary]\n{summary}\n\nContinue with the task."
        })

    def clear(self):
        """Reset to just the system prompt."""
        self._messages = []
        if self.system_prompt:
            self._messages.append({"role": "system", "content": self.system_prompt})

    def message_count(self) -> int:
        return len(self._messages)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_prompt": self.system_prompt,
            "messages": self._messages,
            "max_context_tokens": self.max_context_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionContext":
        ctx = cls(
            system_prompt=data.get("system_prompt", ""),
            max_context_tokens=data.get("max_context_tokens", DEFAULT_MAX_CONTEXT_TOKENS),
        )
        ctx._messages = data.get("messages", [])
        return ctx
