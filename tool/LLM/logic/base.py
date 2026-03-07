"""Base LLM provider interface with unified tracking.

All providers extend ``LLMProvider`` and implement ``_send_request()``.
The base class handles:
  - Usage recording (automatic via ``send()``)
  - Latency measurement
  - Cost estimation
  - Rate limiting hooks
"""
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class CostModel:
    """Per-provider pricing metadata.

    Prices are in USD per 1M tokens.  Set to 0 for free-tier providers.
    ``daily_limit`` and ``monthly_limit`` are token counts (0 = unlimited).
    """
    prompt_price_per_m: float = 0.0
    completion_price_per_m: float = 0.0
    daily_token_limit: int = 0
    monthly_token_limit: int = 0
    free_tier: bool = True

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost in USD for given token counts."""
        return (prompt_tokens * self.prompt_price_per_m / 1_000_000
                + completion_tokens * self.completion_price_per_m / 1_000_000)


class LLMProvider(ABC):
    """Abstract base for LLM backends.

    Subclasses must implement:
      - ``_send_request()`` — the raw API call
      - ``is_available()`` — availability check
      - ``get_info()`` — provider metadata

    The ``send()`` method is final-like: it wraps ``_send_request()``
    with timing, usage recording, and cost estimation.
    """

    name: str = "base"
    cost_model: CostModel = CostModel()

    @abstractmethod
    def _send_request(self, messages: List[Dict[str, str]],
                      temperature: float = 1.0,
                      max_tokens: int = 16384) -> Dict[str, Any]:
        """Execute the raw API call. Subclasses implement this.

        Returns:
            {"ok": bool, "text": str, "usage": dict, "error": str|None,
             "error_code": int (optional)}
        """

    def send(self, messages: List[Dict[str, str]],
             temperature: float = 1.0,
             max_tokens: int = 16384) -> Dict[str, Any]:
        """Send a conversation with automatic tracking.

        Wraps ``_send_request()`` with:
        - Latency measurement
        - Usage recording to the persistent tracker
        - Cost estimation appended to the result
        """
        t0 = time.time()
        result = self._send_request(messages, temperature, max_tokens)
        latency = time.time() - t0

        result.setdefault("latency_s", round(latency, 3))

        usage = result.get("usage", {})
        prompt_tok = usage.get("prompt_tokens", 0)
        completion_tok = usage.get("completion_tokens", 0)
        result["estimated_cost_usd"] = self.cost_model.estimate_cost(
            prompt_tok, completion_tok)

        try:
            from tool.LLM.logic.usage import record_usage
            model = result.get("model", getattr(self, "_model", self.name))
            api_key = getattr(self, "_api_key", "")
            record_usage(self.name, model, result, latency, api_key=api_key)
        except Exception:
            pass

        return result

    def stream(self, messages: List[Dict[str, str]],
               temperature: float = 1.0,
               max_tokens: int = 16384):
        """Stream a conversation, yielding text chunks with tracking.

        Yields ``{"ok": True, "text": "chunk"}`` for each token/chunk.
        After the stream ends, records usage.  The final yield includes
        ``"done": True`` and aggregated metadata.

        Parameters
        ----------
        messages : list
            OpenAI-format message list.
        temperature : float
            Sampling temperature.
        max_tokens : int
            Max output tokens.

        Yields
        ------
        dict
            ``{"ok": True, "text": "..."}`` per chunk.
            Final chunk adds ``{"done": True, "full_text": "...", "usage": {...}}``.
        """
        t0 = time.time()
        full_text_parts = []
        chunk_count = 0
        ttft = None
        last_error = None

        for chunk in self.send_streaming(messages, temperature, max_tokens):
            if not chunk.get("ok"):
                last_error = chunk.get("error", "Stream error")
                yield chunk
                return

            text = chunk.get("text", "")
            if text:
                if ttft is None:
                    ttft = time.time() - t0
                full_text_parts.append(text)
                chunk_count += 1
                yield {"ok": True, "text": text}

        latency = time.time() - t0
        full_text = "".join(full_text_parts)

        estimated_tokens = len(full_text) // 4
        usage = {"completion_tokens": estimated_tokens, "total_tokens": estimated_tokens}
        result_for_record = {
            "ok": True, "text": full_text,
            "model": getattr(self, "_model", self.name),
            "usage": usage,
        }

        try:
            from tool.LLM.logic.usage import record_usage
            model = getattr(self, "_model", self.name)
            api_key = getattr(self, "_api_key", "")
            record_usage(self.name, model, result_for_record, latency, api_key=api_key)
        except Exception:
            pass

        yield {
            "ok": True, "text": "", "done": True,
            "full_text": full_text,
            "usage": usage,
            "latency_s": round(latency, 3),
            "ttft_s": round(ttft, 3) if ttft else None,
            "chunk_count": chunk_count,
            "estimated_cost_usd": self.cost_model.estimate_cost(0, estimated_tokens),
        }

    def send_streaming(self, messages: List[Dict[str, str]],
                       temperature: float = 1.0,
                       max_tokens: int = 16384):
        """Raw streaming generator. Override in subclasses.

        Default implementation falls back to non-streaming ``send()``,
        yielding the entire response as a single chunk.
        """
        result = self.send(messages, temperature, max_tokens)
        if result.get("ok"):
            yield {"ok": True, "text": result.get("text", "")}
        else:
            yield {"ok": False, "error": result.get("error", "Unknown error")}

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether this provider is configured and reachable."""

    def get_info(self) -> Dict[str, Any]:
        """Return provider metadata."""
        return {
            "name": self.name,
            "available": self.is_available(),
            "cost_model": {
                "prompt_price_per_m": self.cost_model.prompt_price_per_m,
                "completion_price_per_m": self.cost_model.completion_price_per_m,
                "free_tier": self.cost_model.free_tier,
                "daily_token_limit": self.cost_model.daily_token_limit,
                "monthly_token_limit": self.cost_model.monthly_token_limit,
            },
        }

    def get_daily_cost(self) -> float:
        """Calculate today's estimated cost from usage records."""
        try:
            from tool.LLM.logic.usage import get_daily_summary
            summary = get_daily_summary(provider=self.name)
            return self.cost_model.estimate_cost(
                summary.get("prompt_tokens", 0),
                summary.get("completion_tokens", 0),
            )
        except Exception:
            return 0.0
