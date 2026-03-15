"""OpenAI-compatible provider base class.

Many LLM providers offer OpenAI-compatible chat completions endpoints.
This base class provides a reusable implementation that subclasses
customize via class attributes:

    API_URL:       The chat completions endpoint
    MODEL_ID:      The model identifier string
    CONFIG_VENDOR: The vendor key in LLM config (for API key storage)
    DEFAULT_RPM:   Rate limit (requests per minute)

Handles both synchronous and streaming requests via urllib (no SDK dependency).
"""
import json
import os
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

from tool.LLM.logic.base import LLMProvider, CostModel, ModelCapabilities
from tool.LLM.logic.rate_limiter import RateLimiter
from tool.LLM.logic.config import get_config_value, set_config_value, APIKeyRotator


class OpenAICompatProvider(LLMProvider):
    """Base for providers with OpenAI-compatible chat/completions API."""

    API_URL: str = ""
    MODEL_ID: str = ""
    CONFIG_VENDOR: str = ""
    CONFIG_KEY_ENV: str = ""
    DEFAULT_RPM: int = 30
    DEFAULT_MAX_CONTEXT: int = 8192
    DEFAULT_MAX_OUTPUT: int = 4096
    REQUEST_TIMEOUT: int = 120

    name: str = "openai-compat"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_streaming=True,
    )

    def __init__(self, api_key: Optional[str] = None,
                 rpm: int = 0, **kwargs):
        self._key_rotator = APIKeyRotator(self.CONFIG_VENDOR) if self.CONFIG_VENDOR else None
        self._api_key = (
            api_key
            or (self._key_rotator.current_key if self._key_rotator else None)
            or self._get_stored_key()
        )
        self._model = self.MODEL_ID
        self._rate_limiter = RateLimiter(
            rpm=rpm or self.DEFAULT_RPM, min_interval_s=2.0, jitter_s=1.0
        )

    def _get_stored_key(self) -> Optional[str]:
        key = get_config_value(f"{self.CONFIG_VENDOR}_api_key")
        if not key and self.CONFIG_KEY_ENV:
            key = os.environ.get(self.CONFIG_KEY_ENV)
        return key if key else None

    @classmethod
    def save_api_key(cls, key: str):
        set_config_value(f"{cls.CONFIG_VENDOR}_api_key", key)

    @classmethod
    def get_api_key(cls) -> Optional[str]:
        key = get_config_value(f"{cls.CONFIG_VENDOR}_api_key")
        if not key and cls.CONFIG_KEY_ENV:
            key = os.environ.get(cls.CONFIG_KEY_ENV)
        return key if key else None

    def is_available(self) -> bool:
        return bool(self._api_key)

    def get_info(self) -> Dict[str, Any]:
        info = super().get_info()
        info.update({
            "model": self._model,
            "api_url": self.API_URL,
            "rpm_limit": self._rate_limiter.rpm,
            "max_context": self.DEFAULT_MAX_CONTEXT,
        })
        return info

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _send_request(self, messages: List[Dict[str, str]],
                      temperature: float = 0.7,
                      max_tokens: int = 0,
                      tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self._api_key:
            return {"ok": False, "text": "",
                    "error": f"No {self.CONFIG_VENDOR} API key configured."}

        self._rate_limiter.wait()

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.DEFAULT_MAX_OUTPUT,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.API_URL, data=data,
            headers=self._build_headers(), method="POST"
        )

        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.REQUEST_TIMEOUT) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err_body = ""
            if e.fp:
                try:
                    err_body = e.read().decode()
                except Exception:
                    pass
            self._rate_limiter.release()
            if e.code == 429:
                return {"ok": False, "text": "", "error_code": 429,
                        "error": f"Rate limited (429). {err_body}"}
            return {"ok": False, "text": "", "error_code": e.code,
                    "error": f"API error ({e.code}): {err_body}"}
        except Exception as e:
            self._rate_limiter.release()
            return {"ok": False, "text": "", "error": str(e)}

        self._rate_limiter.release()
        latency = time.time() - t0

        choices = body.get("choices", [])
        if not choices:
            return {"ok": False, "text": "", "error": "No choices in response."}

        msg = choices[0].get("message", {})
        text = msg.get("content", "") or ""
        usage = body.get("usage", {})

        result: Dict[str, Any] = {
            "ok": True,
            "text": text,
            "usage": usage,
            "model": self._model,
            "finish_reason": choices[0].get("finish_reason", ""),
            "latency_s": round(latency, 2),
        }
        if msg.get("tool_calls"):
            result["tool_calls"] = msg["tool_calls"]
        return result

    def send_streaming(self, messages: List[Dict[str, str]],
                       temperature: float = 0.7,
                       max_tokens: int = 0,
                       tools: List[Dict[str, Any]] = None):
        if not self._api_key:
            yield {"ok": False, "error": f"No {self.CONFIG_VENDOR} API key."}
            return

        self._rate_limiter.wait()

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.DEFAULT_MAX_OUTPUT,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        data = json.dumps(payload).encode("utf-8")
        headers = self._build_headers()
        headers["Accept"] = "text/event-stream"
        req = urllib.request.Request(
            self.API_URL, data=data, headers=headers, method="POST"
        )

        try:
            resp = urllib.request.urlopen(req, timeout=self.REQUEST_TIMEOUT)
        except urllib.error.HTTPError as e:
            self._rate_limiter.release()
            err_body = ""
            if e.fp:
                try:
                    err_body = e.read().decode()
                except Exception:
                    pass
            yield {"ok": False, "error_code": e.code,
                   "error": f"HTTP {e.code}: {err_body}"}
            return
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
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    tc = delta.get("tool_calls")
                    if tc:
                        yield {"ok": True, "tool_calls": tc}
                    elif content:
                        yield {"ok": True, "text": content}
                except Exception:
                    continue
            if last_usage:
                yield {"ok": True, "text": "", "usage": last_usage}
        finally:
            resp.close()
            self._rate_limiter.release()

    @classmethod
    def validate_key(cls, api_key: str) -> Dict[str, Any]:
        """Validate an API key by making a minimal request.

        Returns {"ok": True} on success, {"ok": False, "error": "..."} on failure.
        """
        payload = {
            "model": cls.MODEL_ID,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(
            cls.API_URL, data=data, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())
                if body.get("choices"):
                    return {"ok": True, "model": cls.MODEL_ID}
                return {"ok": False, "error": "Unexpected response format"}
        except urllib.error.HTTPError as e:
            err = ""
            if e.fp:
                try:
                    err = e.read().decode()[:200]
                except Exception:
                    pass
            if e.code == 401:
                return {"ok": False, "error": "Invalid API key (401 Unauthorized)"}
            if e.code == 403:
                return {"ok": False, "error": "Access denied (403 Forbidden)"}
            return {"ok": False, "error": f"HTTP {e.code}: {err}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
