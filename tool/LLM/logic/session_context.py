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

    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """Return the current messages array for sending to the API."""
        return list(self._messages)

    def _estimate_tokens(self) -> int:
        total = 0
        for m in self._messages:
            total += len(m.get("content", "")) // APPROX_CHARS_PER_TOKEN + 4
        return total

    def _trim(self):
        """Remove older messages (keeping system prompt) if over limit."""
        while (self._estimate_tokens() > self.max_context_tokens
               and len(self._messages) > 2):
            if self._messages[0].get("role") == "system":
                if len(self._messages) > 2:
                    self._messages.pop(1)
                else:
                    break
            else:
                self._messages.pop(0)

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
