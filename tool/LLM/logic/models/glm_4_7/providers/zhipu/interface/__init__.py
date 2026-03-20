"""GLM-4.7 provider via Zhipu AI direct API.

Endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions
Model:    glm-4.7 (MoE, 200K context, 128K output)
Docs:     https://docs.bigmodel.cn/cn/guide/models/text/glm-4.7

Uses the zhipuai SDK if available, otherwise falls back to urllib.
"""
import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from tool.LLM.logic.base import LLMProvider, CostModel, ModelCapabilities
from tool.LLM.logic.rate_limiter import RateLimiter
from tool.LLM.logic.config import get_config_value, set_config_value

ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL_ID = "glm-4.7"
DEFAULT_RPM = 30
DEFAULT_MAX_CONTEXT = 200000
DEFAULT_MAX_OUTPUT = 16384

_zhipuai = None


def _try_import_sdk():
    global _zhipuai
    if _zhipuai is not None:
        return _zhipuai
    try:
        import zhipuai
        _zhipuai = zhipuai
        return zhipuai
    except ImportError:
        _zhipuai = False
        return False


def get_api_key() -> Optional[str]:
    key = get_config_value("zhipu_api_key") or os.environ.get("ZHIPU_API_KEY")
    return key if key else None


def save_api_key(key: str):
    set_config_value("zhipu_api_key", key)


class ZhipuGLM47Provider(LLMProvider):
    """GLM-4.7 via Zhipu AI direct API.

    Prefers the zhipuai SDK for richer error handling and SSE streaming.
    Falls back to urllib if the SDK is not installed.
    """

    name = "zhipu-glm-4.7"
    cost_model = CostModel(free_tier=False)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=DEFAULT_MAX_CONTEXT,
        max_output_tokens=DEFAULT_MAX_OUTPUT,
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
        self._client = None
        sdk = _try_import_sdk()
        if sdk and self._api_key:
            try:
                import httpx
                self._client = sdk.ZhipuAI(
                    api_key=self._api_key,
                    timeout=httpx.Timeout(timeout=120.0, connect=10.0),
                )
            except Exception:
                try:
                    self._client = sdk.ZhipuAI(api_key=self._api_key)
                except Exception:
                    self._client = None

    def is_available(self) -> bool:
        return bool(self._api_key)

    def get_info(self) -> Dict[str, Any]:
        info = super().get_info()
        info.update({
            "model": self._model,
            "api_url": ZHIPU_API_URL,
            "rpm_limit": self._rate_limiter.rpm,
            "max_context": DEFAULT_MAX_CONTEXT,
            "sdk_available": self._client is not None,
        })
        return info

    def _send_request(self, messages: List[Dict[str, str]],
                      temperature: float = 0.7,
                      max_tokens: int = DEFAULT_MAX_OUTPUT,
                      tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self._api_key:
            return {"ok": False, "text": "",
                    "error": "No Zhipu API key. Run LLM setup."}

        self._rate_limiter.wait()

        if self._client:
            return self._send_via_sdk(messages, temperature, max_tokens, tools)
        return self._send_via_urllib(messages, temperature, max_tokens, tools)

    def _send_via_sdk(self, messages, temperature, max_tokens, tools):
        """Send using the zhipuai SDK."""
        try:
            kwargs = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }
            if tools:
                kwargs["tools"] = tools

            response = self._client.chat.completions.create(**kwargs)

            if not response or not response.choices:
                return {"ok": False, "text": "",
                        "error": "No choices in response."}

            choice = response.choices[0]
            msg = choice.message
            text = msg.content or ""
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            result = {
                "ok": True,
                "text": text,
                "usage": usage,
                "model": self._model,
                "finish_reason": choice.finish_reason or "",
            }
            if msg.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            return result

        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg:
                return {"ok": False, "text": "", "error_code": 429,
                        "error": f"Rate limited (429). {err_msg}"}
            return {"ok": False, "text": "", "error": err_msg}

    def _send_via_urllib(self, messages, temperature, max_tokens, tools):
        """Fallback: send using urllib (no SDK dependency)."""
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
            ZHIPU_API_URL, data=data, headers=headers, method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
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
            return {"ok": False, "text": "", "error": str(e)}

        choices = body.get("choices", [])
        if not choices:
            return {"ok": False, "text": "", "error": "No choices in response."}

        msg = choices[0].get("message", {})
        text = msg.get("content", "")
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
                       max_tokens: int = DEFAULT_MAX_OUTPUT,
                       tools: List[Dict[str, Any]] = None):
        if not self._api_key:
            yield {"ok": False, "error": "No API key configured."}
            return

        self._rate_limiter.wait()

        if self._client:
            yield from self._stream_via_sdk(messages, temperature, max_tokens, tools)
        else:
            yield from self._stream_via_urllib(messages, temperature, max_tokens, tools)

    def _stream_via_sdk(self, messages, temperature, max_tokens, tools):
        """Stream using the zhipuai SDK."""
        import queue
        import threading

        CHUNK_TIMEOUT = 90

        try:
            kwargs = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }
            if tools:
                kwargs["tools"] = tools

            response = self._client.chat.completions.create(**kwargs)

            q: queue.Queue = queue.Queue()
            _SENTINEL = object()

            def _reader():
                try:
                    for chunk in response:
                        q.put(chunk)
                    q.put(_SENTINEL)
                except Exception as exc:
                    q.put(exc)

            t = threading.Thread(target=_reader, daemon=True)
            t.start()

            last_usage = {}
            while True:
                try:
                    item = q.get(timeout=CHUNK_TIMEOUT)
                except queue.Empty:
                    yield {"ok": False,
                           "error": f"Stream timeout ({CHUNK_TIMEOUT}s between chunks)"}
                    return
                if item is _SENTINEL:
                    break
                if isinstance(item, Exception):
                    yield {"ok": False, "error": str(item)}
                    return

                chunk = item
                if hasattr(chunk, "usage") and chunk.usage:
                    last_usage = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    }
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.tool_calls:
                    yield {"ok": True, "tool_calls": [
                        {
                            "index": tc.index,
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in delta.tool_calls
                        if tc.function
                    ]}
                elif delta.content:
                    yield {"ok": True, "text": delta.content}
            if last_usage:
                yield {"ok": True, "text": "", "usage": last_usage}
        except Exception as e:
            yield {"ok": False, "error": str(e)}

    def _stream_via_urllib(self, messages, temperature, max_tokens, tools):
        """Fallback streaming via urllib."""
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
            ZHIPU_API_URL, data=data, headers=headers, method="POST"
        )

        try:
            resp = urllib.request.urlopen(req, timeout=120)
        except Exception as e:
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
