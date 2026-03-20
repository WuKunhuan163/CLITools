"""Anthropic Messages API provider base class.

Anthropic uses a different API format than OpenAI:
- Auth via x-api-key header (not Bearer)
- POST /v1/messages (not /v1/chat/completions)
- Response uses content[] blocks (not choices[].message)
- anthropic-version header required

Handles both synchronous and streaming via urllib (no SDK dependency).
"""
import json
import os
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

from tool.LLM.logic.base import LLMProvider, CostModel, ModelCapabilities
from tool.LLM.logic.rate.limiter import RateLimiter
from tool.LLM.logic.config import get_config_value, set_config_value
from tool.LLM.logic.rate.key_state import get_selector, KeyStatus
from tool.LLM.logic.providers.manager import get_manager


class AnthropicProvider(LLMProvider):
    """Base for Anthropic Claude models via the Messages API."""

    API_URL: str = "https://api.anthropic.com/v1/messages"
    MODEL_ID: str = ""
    CONFIG_VENDOR: str = "anthropic"
    CONFIG_KEY_ENV: str = "ANTHROPIC_API_KEY"
    API_VERSION: str = "2023-06-01"
    DEFAULT_RPM: int = 50
    DEFAULT_MAX_CONTEXT: int = 200000
    DEFAULT_MAX_OUTPUT: int = 8192
    REQUEST_TIMEOUT: int = 120

    name: str = "anthropic-base"
    cost_model = CostModel(free_tier=False)
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
            try:
                selector = get_selector(self.CONFIG_VENDOR)
                kid, key = selector.select()
                self._api_key = key
                self._key_id = kid
            except Exception:
                self._api_key = self._get_stored_key()
        else:
            self._api_key = self._get_stored_key()
        self._model = self.MODEL_ID
        try:
            mgr = get_manager()
            existing = mgr._rate_limiters.get(self.name)
            if existing:
                self._rate_limiter = existing
            else:
                self._rate_limiter = RateLimiter(
                    rpm=rpm or self.DEFAULT_RPM, min_interval_s=1.0, jitter_s=0.5
                )
                mgr.register_rate_limiter(self.name, self._rate_limiter)
        except Exception:
            self._rate_limiter = RateLimiter(
                rpm=rpm or self.DEFAULT_RPM, min_interval_s=1.0, jitter_s=0.5
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
            try:
                selector = get_selector(self.CONFIG_VENDOR)
                if not selector.has_usable_keys():
                    return False
            except Exception:
                pass
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
            "x-api-key": self._api_key or "",
            "anthropic-version": self.API_VERSION,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AITerminalTools/1.0",
        }

    @staticmethod
    def _convert_messages(messages: List[Dict[str, str]]):
        """Split system message from user/assistant messages.

        Anthropic requires system as a top-level param, not in messages.
        """
        system_text = ""
        filtered = []
        for m in messages:
            if m.get("role") == "system":
                system_text += (m.get("content", "") + "\n")
            else:
                filtered.append({"role": m["role"], "content": m.get("content", "")})
        return system_text.strip(), filtered

    def _send_request(self, messages: List[Dict[str, str]],
                      temperature: float = 0.7,
                      max_tokens: int = 0,
                      tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self._api_key:
            return {"ok": False, "text": "",
                    "error": f"No {self.CONFIG_VENDOR} API key configured."}

        self._rate_limiter.wait()

        effective_max = min(max_tokens, self.DEFAULT_MAX_OUTPUT) if max_tokens else self.DEFAULT_MAX_OUTPUT
        system_text, api_messages = self._convert_messages(messages)

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": api_messages,
            "max_tokens": effective_max,
        }
        if system_text:
            payload["system"] = system_text
        if temperature is not None:
            payload["temperature"] = temperature
        if tools:
            payload["tools"] = self._convert_tools(tools)

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

        text = self._extract_text(body)
        usage = body.get("usage", {})
        mapped_usage = {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
        }

        result: Dict[str, Any] = {
            "ok": True,
            "text": text,
            "usage": mapped_usage,
            "model": self._model,
            "finish_reason": body.get("stop_reason", ""),
            "latency_s": round(latency, 2),
        }

        tool_calls = self._extract_tool_calls(body)
        if tool_calls:
            result["tool_calls"] = tool_calls

        self._report_to_selector(result, resp_headers)
        return result

    @staticmethod
    def _extract_text(body: Dict) -> str:
        """Extract text from Anthropic content blocks."""
        content = body.get("content", [])
        parts = []
        for block in content:
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)

    @staticmethod
    def _extract_tool_calls(body: Dict) -> List[Dict]:
        """Extract tool_use blocks and convert to OpenAI-style tool_calls."""
        content = body.get("content", [])
        calls = []
        for block in content:
            if block.get("type") == "tool_use":
                calls.append({
                    "id": block.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": json.dumps(block.get("input", {})),
                    },
                })
        return calls

    @staticmethod
    def _convert_tools(tools: List[Dict]) -> List[Dict]:
        """Convert OpenAI-style tools to Anthropic format."""
        result = []
        for tool in tools:
            fn = tool.get("function", tool)
            result.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {}),
            })
        return result

    def _report_to_selector(self, result: Dict[str, Any],
                            headers: Dict[str, str] = None):
        if self._key_id and self.CONFIG_VENDOR:
            try:
                selector = get_selector(self.CONFIG_VENDOR)
                selector.report(self._key_id, result, headers=headers)
            except Exception:
                pass
        try:
            get_manager().report_result(self.name, self._key_id, result, headers)
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
        system_text, api_messages = self._convert_messages(messages)

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": api_messages,
            "max_tokens": effective_max,
            "stream": True,
        }
        if system_text:
            payload["system"] = system_text
        if temperature is not None:
            payload["temperature"] = temperature
        if tools:
            payload["tools"] = self._convert_tools(tools)

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
        stream_ok = True
        try:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or line.startswith(":"):
                    continue
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                    if event_type == "message_stop":
                        break
                    continue
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    evt = chunk.get("type", "")
                    if evt == "content_block_delta":
                        delta = chunk.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield {"ok": True, "text": delta.get("text", "")}
                        elif delta.get("type") == "input_json_delta":
                            pass
                    elif evt == "message_delta":
                        usage = chunk.get("usage", {})
                        if usage:
                            yield {"ok": True, "text": "", "usage": {
                                "prompt_tokens": usage.get("input_tokens", 0),
                                "completion_tokens": usage.get("output_tokens", 0),
                                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                            }}
                except Exception:
                    continue
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
        """Validate an API key by making a minimal request."""
        payload = {
            "model": cls.MODEL_ID,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "x-api-key": api_key,
            "anthropic-version": cls.API_VERSION,
            "Content-Type": "application/json",
            "User-Agent": "AITerminalTools/1.0",
        }
        req = urllib.request.Request(
            cls.API_URL, data=data, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())
                if body.get("content"):
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
