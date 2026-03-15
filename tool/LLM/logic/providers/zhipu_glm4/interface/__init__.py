"""GLM-4-Flash provider via Zhipu AI (OpenAI-compatible).

Endpoint: https://open.bigmodel.cn/api/paas/v4/chat/completions
Model:    glm-4-flash (free tier)
Limits:   Free tier with rate limits, 128K context window
Docs:     https://bigmodel.cn/dev/api/normal-model/glm-4
"""
import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from tool.LLM.logic.base import LLMProvider, CostModel, ModelCapabilities
from tool.LLM.logic.rate_limiter import RateLimiter
from tool.LLM.logic.config import get_config_value, set_config_value, APIKeyRotator

ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL_ID = "glm-4-flash"
DEFAULT_RPM = 30
DEFAULT_MAX_CONTEXT = 128000

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


class ZhipuGLM4Provider(LLMProvider):
    """GLM-4-Flash via Zhipu AI free API."""

    name = "zhipu-glm-4-flash"
    cost_model = CostModel(free_tier=True)
    capabilities = ModelCapabilities(
        supports_tool_calling=True,
        supports_vision=False,
        supports_streaming=True,
        max_context_tokens=128000,
        max_output_tokens=4096,
    )

    def __init__(self, api_key: Optional[str] = None,
                 rpm: int = DEFAULT_RPM,
                 min_interval_s: float = 2.0,
                 jitter_s: float = 1.0):
        self._key_rotator = APIKeyRotator("zhipu")
        self._api_key = api_key or self._key_rotator.current_key or get_api_key()
        self._model = MODEL_ID

        model_config = self._load_model_json()
        if model_config:
            self._rate_limiter = RateLimiter.from_model_json(model_config, "free")
        else:
            self._rate_limiter = RateLimiter(
                rpm=rpm, min_interval_s=min_interval_s, jitter_s=jitter_s
            )

        self._client = None
        self._sdk = _try_import_sdk()
        self._init_client()

    def _init_client(self):
        self._client = None
        if self._sdk and self._api_key:
            try:
                self._client = self._sdk.ZhipuAI(api_key=self._api_key)
            except Exception:
                pass

    def _rotate_key_on_429(self):
        """On 429, try the next API key if available."""
        if self._key_rotator.key_count > 1:
            self._key_rotator.advance()
            new_key = self._key_rotator.current_key
            if new_key and new_key != self._api_key:
                self._api_key = new_key
                self._init_client()
                return True
        return False

    @staticmethod
    def _load_model_json() -> Optional[dict]:
        try:
            p = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model.json")
            with open(p) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

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
                      max_tokens: int = 4096,
                      tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self._api_key:
            return {"ok": False, "text": "",
                    "error": "No Zhipu API key. Run LLM setup."}

        ctx_tokens = self._estimate_tokens(messages)
        self._rate_limiter.wait(context_tokens=ctx_tokens)

        try:
            if self._client:
                result = self._send_via_sdk(messages, temperature, max_tokens, tools)
            else:
                result = self._send_via_urllib(messages, temperature, max_tokens, tools)

            if result.get("error_code") == 429 and self._rotate_key_on_429():
                self._rate_limiter.report_429()
                if self._client:
                    result = self._send_via_sdk(messages, temperature, max_tokens, tools)
                else:
                    result = self._send_via_urllib(messages, temperature, max_tokens, tools)
            return result
        finally:
            self._rate_limiter.release()

    @staticmethod
    def _estimate_tokens(messages: list) -> int:
        """Rough token estimation: ~4 chars per English token, ~2 per CJK."""
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return total_chars // 3

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
        """Fallback: send using urllib."""
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
                       max_tokens: int = 4096,
                       tools: List[Dict[str, Any]] = None):
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
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    tc = delta.get("tool_calls")
                    if tc:
                        yield {"ok": True, "tool_calls": tc}
                    elif content:
                        yield {"ok": True, "text": content}
                except Exception:
                    continue
        finally:
            resp.close()
