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
from tool.LLM.logic.key_state import get_selector, KeyStatus


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
    MAX_TOKENS_PARAM: str = "max_tokens"

    name: str = "openai-compat"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_streaming=True,
    )

    def __init__(self, api_key: Optional[str] = None,
                 rpm: int = 0, **kwargs):
        self._explicit_key = api_key
        self._key_id: Optional[str] = None
        if api_key:
            self._api_key = api_key
        elif self.CONFIG_VENDOR:
            selector = get_selector(self.CONFIG_VENDOR)
            kid, key = selector.select()
            self._api_key = key
            self._key_id = kid
        else:
            self._api_key = self._get_stored_key()
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
        if not self._api_key:
            return False
        if self.CONFIG_VENDOR:
            selector = get_selector(self.CONFIG_VENDOR)
            if not selector.has_usable_keys():
                return False
        return True

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
            "User-Agent": "AITerminalTools/1.0",
        }

    def _send_request(self, messages: List[Dict[str, str]],
                      temperature: float = 0.7,
                      max_tokens: int = 0,
                      tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self._api_key:
            return {"ok": False, "text": "",
                    "error": f"No {self.CONFIG_VENDOR} API key configured."}

        self._rate_limiter.wait()

        effective_max = min(max_tokens, self.DEFAULT_MAX_OUTPUT) if max_tokens else self.DEFAULT_MAX_OUTPUT
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            self.MAX_TOKENS_PARAM: effective_max,
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
        resp_headers = {}
        try:
            with urllib.request.urlopen(req, timeout=self.REQUEST_TIMEOUT) as resp:
                resp_headers = {k.lower(): v for k, v in resp.getheaders()}
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err_body = ""
            err_headers = {}
            if e.fp:
                try:
                    err_headers = {k.lower(): v for k, v in e.headers.items()}
                    err_body = e.read().decode()
                except Exception:
                    pass
            self._rate_limiter.release()
            if e.code == 429:
                self._rate_limiter.report_429()
            result = {"ok": False, "text": "", "error_code": e.code,
                      "error": f"Rate limited (429). {err_body}" if e.code == 429
                      else f"API error ({e.code}): {err_body}"}
            self._report_to_selector(result, err_headers)
            return result
        except Exception as e:
            self._rate_limiter.release()
            result = {"ok": False, "text": "", "error": str(e)}
            self._report_to_selector(result)
            return result

        self._rate_limiter.release()
        self._rate_limiter.report_success()
        latency = time.time() - t0

        choices = body.get("choices", [])
        if not choices:
            result = {"ok": False, "text": "", "error": "No choices in response."}
            self._report_to_selector(result, resp_headers)
            return result

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

        self._report_to_selector(result, resp_headers)
        return result

    def _report_to_selector(self, result: Dict[str, Any],
                            headers: Dict[str, str] = None):
        """Report result back to the adaptive key selector."""
        if self._key_id and self.CONFIG_VENDOR:
            try:
                selector = get_selector(self.CONFIG_VENDOR)
                selector.report(self._key_id, result, headers=headers)
            except Exception:
                pass

    def send_streaming(self, messages: List[Dict[str, str]],
                       temperature: float = 0.7,
                       max_tokens: int = 0,
                       tools: List[Dict[str, Any]] = None):
        if not self._api_key:
            yield {"ok": False, "error": f"No {self.CONFIG_VENDOR} API key."}
            return

        self._rate_limiter.wait()

        effective_max = min(max_tokens, self.DEFAULT_MAX_OUTPUT) if max_tokens else self.DEFAULT_MAX_OUTPUT
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            self.MAX_TOKENS_PARAM: effective_max,
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
            if e.code == 429:
                self._rate_limiter.report_429()
            err_body = ""
            err_headers = {}
            if e.fp:
                try:
                    err_headers = {k.lower(): v for k, v in e.headers.items()}
                    err_body = e.read().decode()
                except Exception:
                    pass
            result = {"ok": False, "error_code": e.code,
                      "error": f"HTTP {e.code}: {err_body}"}
            self._report_to_selector(result, err_headers)
            yield result
            return
        except Exception as e:
            self._rate_limiter.release()
            result = {"ok": False, "error": str(e)}
            self._report_to_selector(result)
            yield result
            return

        resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        last_usage = {}
        stream_ok = True
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
        except Exception:
            stream_ok = False
        finally:
            resp.close()
            self._rate_limiter.release()
            if stream_ok:
                self._rate_limiter.report_success()
            self._report_to_selector(
                {"ok": stream_ok, "latency_s": 0}, resp_headers)

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
            "User-Agent": "AITerminalTools/1.0",
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
