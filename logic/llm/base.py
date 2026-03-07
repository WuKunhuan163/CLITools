"""Base LLM provider interface.

All providers implement ``send()`` which accepts a messages array
and returns the assistant's reply text.  Session (multi-turn context)
is managed by the caller via the messages list.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class LLMProvider(ABC):
    """Abstract base for LLM backends."""

    name: str = "base"

    @abstractmethod
    def send(self, messages: List[Dict[str, str]],
             temperature: float = 1.0,
             max_tokens: int = 16384) -> Dict[str, Any]:
        """Send a conversation and return the model response.

        Args:
            messages: OpenAI-format messages array
                      [{"role": "system"|"user"|"assistant", "content": "..."}]
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.

        Returns:
            {"ok": bool, "text": str, "usage": dict, "error": str|None}
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether this provider is configured and reachable."""

    def get_info(self) -> Dict[str, Any]:
        """Return provider metadata."""
        return {"name": self.name, "available": self.is_available()}
