"""GLM-4.7 provider via NVIDIA Build (OpenAI-compatible).

Endpoint: https://integrate.api.nvidia.com/v1/chat/completions
Model:    z-ai/glm4.7
Limits:   40 RPM (free tier), 131K context window
License:  MIT / NVIDIA Open Model License
"""
import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from tool.LLM.logic.base import LLMProvider, CostModel, ModelCapabilities
from tool.LLM.logic.rate.limiter import RateLimiter
from tool.LLM.logic.config import get_config_value, set_config_value

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_ID = "z-ai/glm4.7"
DEFAULT_RPM = 30
DEFAULT_MAX_CONTEXT = 131072


def get_api_key() -> Optional[str]:
    """Get NVIDIA API key from tool config or environment."""
    key = get_config_value("nvidia_api_key") or os.environ.get("NVIDIA_API_KEY")
    return key if key else None


def save_api_key(key: str):
    """Store the NVIDIA API key in tool config."""
    set_config_value("nvidia_api_key", key)


class NvidiaGLM47Provider(LLMProvider):
    """GLM-4.7 via NVIDIA Build free API."""

    name = "nvidia-glm-4-7b"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=131072,
        max_output_tokens=16384,
    )

    def __init__(self, api_key: Optional[str] = None,
                 rpm: int = DEFAULT_RPM,
                 min_interval_s: float = 2.0,
                 jitter_s: float = 1.0):
        self._api_key = api_key or get_api_key()
        self._rate_limiter = RateLimiter(
            rpm=rpm, min_interval_s=min_interval_s, jitter_s=jitter_s
        )
        self._model = MODEL_ID

    def is_available(self) -> bool:
        return bool(self._api_key)

    def get_info(self) -> Dict[str, Any]:
        info = super().get_info()
        info.update({
            "model": self._model,
            "api_url": NVIDIA_API_URL,
            "rpm_limit": self._rate_limiter.rpm,
            "max_context": DEFAULT_MAX_CONTEXT,
        })
        return info

    def _send_request(self, messages: List[Dict[str, str]],
                      temperature: float = 0.7,
                      max_tokens: int = 16384,
                      tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self._api_key:
            return {"ok": False, "text": "",
                    "error": "No NVIDIA API key. Run LLM setup."}

        self._rate_limiter.wait()

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        req = urllib.request.Request(
            NVIDIA_API_URL, data=data, headers=headers, method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            self._rate_limiter.release()
            err_body = ""
            if e.fp:
                try:
                    err_body = e.read().decode()
                except Exception:
                    pass
            if e.code == 429:
                return {"ok": False, "text": "", "error_code": e.code,
                        "error": f"Rate limited (429). {err_body}"}
            return {"ok": False, "text": "", "error_code": e.code,
                    "error": f"API error ({e.code}): {err_body}"}
        except Exception as e:
            self._rate_limiter.release()
            return {"ok": False, "text": "", "error": str(e)}

        self._rate_limiter.release()

        choices = body.get("choices", [])
        if not choices:
            return {"ok": False, "text": "", "error": "No choices in response."}

        msg = choices[0].get("message", {}) or {}
        text = msg.get("content", "") or ""
        usage = body.get("usage", {})

        result = {
            "ok": True,
            "text": text,
            "usage": usage,
            "model": self._model,
            "finish_reason": choices[0].get("finish_reason", ""),
        }
        if msg.get("tool_calls"):
            result["tool_calls"] = msg["tool_calls"]
        return result

    def send_streaming(self, messages: List[Dict[str, str]],
                       temperature: float = 0.7,
                       max_tokens: int = 16384,
                       tools: List[Dict[str, Any]] = None):
        """Generator that yields text/tool_call chunks from a streaming response."""
        if not self._api_key:
            yield {"ok": False, "error": "No API key configured."}
            return

        self._rate_limiter.wait()

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = tools

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }

        req = urllib.request.Request(
            NVIDIA_API_URL, data=data, headers=headers, method="POST"
        )

        try:
            resp = urllib.request.urlopen(req, timeout=120)
        except Exception as e:
            self._rate_limiter.release()
            yield {"ok": False, "error": str(e)}
            return

        last_usage = {}
        try:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    if chunk.get("usage"):
                        last_usage = chunk["usage"]
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {}) or {}
                    content = delta.get("content", "") or ""
                    reasoning = delta.get("reasoning_content", "")
                    tc = delta.get("tool_calls")
                    if tc:
                        yield {"ok": True, "tool_calls": tc}
                    if reasoning:
                        yield {"ok": True, "reasoning": reasoning}
                    if content:
                        yield {"ok": True, "text": content}
                except Exception:
                    continue
            if last_usage:
                yield {"ok": True, "text": "", "usage": last_usage}
        finally:
            resp.close()
            self._rate_limiter.release()


"""NVIDIA GLM-4.7 context pipeline.

Currently a pass-through — NVIDIA GLM-4.7 handles multi-turn tool
calling correctly. Override if issues are discovered.
"""
from tool.LLM.logic.pipeline import ContextPipeline


class NvidiaContextPipeline(ContextPipeline):
    """Pipeline for NVIDIA GLM-4.7 — pass-through."""
    pass
