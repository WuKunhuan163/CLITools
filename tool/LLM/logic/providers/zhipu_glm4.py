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

from tool.LLM.logic.base import LLMProvider, CostModel
from tool.LLM.logic.rate_limiter import RateLimiter
from tool.LLM.logic.config import get_config_value, set_config_value

ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL_ID = "glm-4-flash"
DEFAULT_RPM = 30
DEFAULT_MAX_CONTEXT = 128000


def get_api_key() -> Optional[str]:
    key = get_config_value("zhipu_api_key") or os.environ.get("ZHIPU_API_KEY")
    return key if key else None


def save_api_key(key: str):
    set_config_value("zhipu_api_key", key)


class ZhipuGLM4Provider(LLMProvider):
    """GLM-4-Flash via Zhipu AI free API."""

    name = "zhipu_glm4"
    cost_model = CostModel(free_tier=True)

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
            "api_url": ZHIPU_API_URL,
            "rpm_limit": self._rate_limiter.rpm,
            "max_context": DEFAULT_MAX_CONTEXT,
        })
        return info

    def _send_request(self, messages: List[Dict[str, str]],
                      temperature: float = 0.7,
                      max_tokens: int = 4096) -> Dict[str, Any]:
        if not self._api_key:
            return {"ok": False, "text": "",
                    "error": "No Zhipu API key. Run LLM setup."}

        self._rate_limiter.wait()

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

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

        return {
            "ok": True,
            "text": text,
            "usage": usage,
            "model": self._model,
            "finish_reason": choices[0].get("finish_reason", ""),
        }

    def send_streaming(self, messages: List[Dict[str, str]],
                       temperature: float = 0.7,
                       max_tokens: int = 4096):
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
                    if content:
                        yield {"ok": True, "text": content}
                except Exception:
                    continue
        finally:
            resp.close()
