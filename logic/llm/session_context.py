"""Multi-turn session context manager for API-based LLM providers.

Maintains a ``messages`` array in memory, handling:
  - System prompt injection
  - Context truncation when approaching token limits
  - History summarization (optional)
"""
from typing import Dict, Any, List, Optional


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
