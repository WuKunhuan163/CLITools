"""Base LLM provider interface with unified tracking.

All providers extend ``LLMProvider`` and implement ``_send_request()``.
The base class handles:
  - Usage recording (automatic via ``send()``)
  - Latency measurement
  - Cost estimation
  - Rate limiting hooks
"""
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class ModelCapabilities:
    """Flags indicating what a model can do.

    These influence which tools and prompts the conversation layer
    provides to the model. For example, only models with
    ``supports_vision=True`` receive image-based tool schemas.
    """
    supports_tool_calling: bool = False
    supports_vision: bool = False
    supports_streaming: bool = True
    supports_system_prompt: bool = True
    max_context_tokens: int = 32000
    max_output_tokens: int = 4096


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


class ProviderNotImplementedError(NotImplementedError):
    """Raised when a provider directory exists (with assets) but has no implementation yet."""
    pass


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
    capabilities: ModelCapabilities = ModelCapabilities()
    _active_response = None

    def abort_stream(self):
        """Abort the current streaming response by closing the HTTP connection.

        This allows immediate cancellation without waiting for the next chunk.
        Safe to call from any thread.
        """
        resp = self._active_response
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass
            self._active_response = None

    @classmethod
    def icon_path(cls) -> Optional[str]:
        """Return absolute path to this provider's logo SVG, or None.

        Resolution: model dir logo.svg > provider dir logo.svg > assets/logo.svg
        """
        import inspect
        try:
            src = inspect.getfile(cls)
        except (TypeError, OSError):
            return None

        src_dir = os.path.dirname(src)

        # Walk up to find model-level logo.svg (models/<model>/logo.svg)
        parts = src_dir.split(os.sep)
        for i in range(len(parts) - 1, -1, -1):
            if parts[i] == "models" and i + 1 < len(parts):
                model_dir = os.sep.join(parts[:i + 2])
                logo = os.path.join(model_dir, "logo.svg")
                if os.path.isfile(logo):
                    return logo
                break

        # Check provider dir logo.svg
        for i in range(len(parts) - 1, -1, -1):
            if parts[i] == "providers" and i + 1 < len(parts):
                prov_dir = os.sep.join(parts[:i + 2])
                logo = os.path.join(prov_dir, "logo.svg")
                if os.path.isfile(logo):
                    return logo
                break

        # Legacy: assets/logo.svg next to the class file
        logo = os.path.join(src_dir, "assets", "logo.svg")
        return logo if os.path.isfile(logo) else None

    @abstractmethod
    def _send_request(self, messages: List[Dict[str, str]],
                      temperature: float = 1.0,
                      max_tokens: int = 16384,
                      tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the raw API call. Subclasses implement this.

        Returns:
            {"ok": bool, "text": str, "usage": dict, "error": str|None,
             "error_code": int (optional),
             "tool_calls": list (optional — structured tool calls)}
        """

    def send(self, messages: List[Dict[str, str]],
             temperature: float = 1.0,
             max_tokens: int = 16384,
             tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a conversation with automatic tracking.

        Wraps ``_send_request()`` with:
        - Latency measurement
        - Usage recording to the persistent tracker
        - Cost estimation appended to the result
        """
        t0 = time.time()
        result = self._send_request(messages, temperature, max_tokens,
                                    tools=tools)
        latency = time.time() - t0

        result.setdefault("latency_s", round(latency, 3))

        usage = result.get("usage", {})
        prompt_tok = usage.get("prompt_tokens", 0)
        completion_tok = usage.get("completion_tokens", 0)
        result["estimated_cost_usd"] = self.cost_model.estimate_cost(
            prompt_tok, completion_tok)

        try:
            from tool.LLM.logic.session.usage import record_usage
            model = result.get("model", getattr(self, "_model", self.name))
            api_key = getattr(self, "_api_key", "")
            record_usage(self.name, model, result, latency, api_key=api_key)
        except Exception:
            pass

        return result

    def stream(self, messages: List[Dict[str, str]],
               temperature: float = 1.0,
               max_tokens: int = 16384,
               tools: List[Dict[str, Any]] = None):
        """Stream a conversation, yielding text chunks with tracking.

        Yields ``{"ok": True, "text": "chunk"}`` for each token/chunk.
        When the model returns structured tool calls, yields a chunk with
        ``"tool_calls": [...]`` instead of ``"text"``.
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
        tools : list, optional
            OpenAI-format tool schemas for structured tool calling.

        Yields
        ------
        dict
            ``{"ok": True, "text": "..."}`` per chunk.
            Final chunk adds ``{"done": True, "full_text": "...", "usage": {...}}``.
        """
        t0 = time.time()
        full_text_parts = []
        tool_calls_by_index: Dict[int, Dict[str, Any]] = {}
        chunk_count = 0
        ttft = None
        api_usage = None

        for chunk in self.send_streaming(messages, temperature, max_tokens,
                                         tools=tools):
            if not chunk.get("ok"):
                try:
                    from tool.LLM.logic.session.usage import record_usage
                    model = getattr(self, "_model", self.name)
                    api_key = getattr(self, "_api_key", "")
                    record_usage(self.name, model, chunk, 0, api_key=api_key)
                except Exception:
                    pass
                yield chunk
                return

            if chunk.get("_auto_switched"):
                yield chunk
                continue

            if chunk.get("usage"):
                api_usage = chunk["usage"]

            tc = chunk.get("tool_calls")
            if tc:
                for delta in tc:
                    idx = delta.get("index", 0)
                    if idx not in tool_calls_by_index:
                        tool_calls_by_index[idx] = {
                            "id": delta.get("id", ""),
                            "type": delta.get("type", "function"),
                            "function": {
                                "name": delta.get("function", {}).get("name", ""),
                                "arguments": delta.get("function", {}).get("arguments", ""),
                            },
                        }
                    else:
                        existing = tool_calls_by_index[idx]
                        if delta.get("id"):
                            existing["id"] = delta["id"]
                        fn_delta = delta.get("function", {})
                        if fn_delta.get("name"):
                            existing["function"]["name"] = fn_delta["name"]
                        if fn_delta.get("arguments"):
                            existing["function"]["arguments"] += fn_delta["arguments"]
                if ttft is None:
                    ttft = time.time() - t0
                yield {"ok": True, "tool_calls": tc}
                continue

            reasoning = chunk.get("reasoning", "")
            if reasoning:
                if ttft is None:
                    ttft = time.time() - t0
                yield {"ok": True, "reasoning": reasoning}

            text = chunk.get("text", "")
            if text:
                if ttft is None:
                    ttft = time.time() - t0
                full_text_parts.append(text)
                chunk_count += 1
                yield {"ok": True, "text": text}

        latency = time.time() - t0
        full_text = "".join(full_text_parts)
        merged_tool_calls = [tool_calls_by_index[k] for k in sorted(tool_calls_by_index)]

        estimated_tokens = len(full_text) // 4
        usage = api_usage or {"prompt_tokens": 0, "completion_tokens": estimated_tokens, "total_tokens": estimated_tokens}
        result_for_record = {
            "ok": True, "text": full_text,
            "model": getattr(self, "_model", self.name),
            "usage": usage,
        }

        try:
            from tool.LLM.logic.session.usage import record_usage
            model = getattr(self, "_model", self.name)
            api_key = getattr(self, "_api_key", "")
            record_usage(self.name, model, result_for_record, latency, api_key=api_key)
        except Exception:
            pass

        done_chunk = {
            "ok": True, "text": "", "done": True,
            "full_text": full_text,
            "usage": usage,
            "latency_s": round(latency, 3),
            "ttft_s": round(ttft, 3) if ttft else None,
            "chunk_count": chunk_count,
            "estimated_cost_usd": self.cost_model.estimate_cost(0, estimated_tokens),
        }
        if merged_tool_calls:
            done_chunk["tool_calls"] = merged_tool_calls
        yield done_chunk

    def send_streaming(self, messages: List[Dict[str, str]],
                       temperature: float = 1.0,
                       max_tokens: int = 16384,
                       tools: List[Dict[str, Any]] = None):
        """Raw streaming generator. Override in subclasses.

        Default implementation falls back to non-streaming ``send()``,
        yielding the entire response as a single chunk.
        """
        result = self.send(messages, temperature, max_tokens, tools=tools)
        if result.get("ok"):
            out = {"ok": True, "text": result.get("text", "")}
            if result.get("tool_calls"):
                out["tool_calls"] = result["tool_calls"]
            yield out
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
            "capabilities": {
                "tool_calling": self.capabilities.supports_tool_calling,
                "vision": self.capabilities.supports_vision,
                "streaming": self.capabilities.supports_streaming,
                "system_prompt": self.capabilities.supports_system_prompt,
                "max_context_tokens": self.capabilities.max_context_tokens,
                "max_output_tokens": self.capabilities.max_output_tokens,
            },
        }

    def health_check(self) -> Dict[str, Any]:
        """Lightweight health check — minimal cost probe.

        Sends a tiny request to verify API key validity and service availability.
        Override in subclasses for provider-specific checks. Default sends a
        1-token completion request.

        Returns:
            {"healthy": bool, "latency_ms": int, "error": str|None}
        """
        t0 = time.time()
        try:
            result = self._send_request(
                [{"role": "user", "content": "hi"}],
                temperature=0,
                max_tokens=1,
            )
            latency_ms = int((time.time() - t0) * 1000)
            return {
                "healthy": result.get("ok", False),
                "latency_ms": latency_ms,
                "error": result.get("error"),
            }
        except Exception as e:
            latency_ms = int((time.time() - t0) * 1000)
            return {"healthy": False, "latency_ms": latency_ms, "error": str(e)}

    def get_daily_cost(self) -> float:
        """Calculate today's estimated cost from usage records."""
        try:
            from tool.LLM.logic.session.usage import get_daily_summary
            summary = get_daily_summary(provider=self.name)
            return self.cost_model.estimate_cost(
                summary.get("prompt_tokens", 0),
                summary.get("completion_tokens", 0),
            )
        except Exception:
            return 0.0
