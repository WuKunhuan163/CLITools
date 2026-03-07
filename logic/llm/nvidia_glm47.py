"""GLM-4.7 provider via NVIDIA Build (OpenAI-compatible).

Endpoint: https://integrate.api.nvidia.com/v1/chat/completions
Model:    z-ai/glm4.7
Limits:   40 RPM (free tier), 131K context window
License:  MIT / NVIDIA Open Model License

Configuration is stored in the project-level ``data/llm_config.json``
and shared across all tools.
"""
import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional

from logic.llm.base import LLMProvider
from logic.llm.rate_limiter import RateLimiter

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_CONFIG_PATH = _DATA_DIR / "llm_config.json"

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_ID = "z-ai/glm4.7"
DEFAULT_RPM = 30
DEFAULT_MAX_CONTEXT = 131072


def _load_config() -> Dict[str, Any]:
    if _CONFIG_PATH.exists():
        try:
            return json.loads(_CONFIG_PATH.read_text())
        except Exception:
            pass
    return {}


def _save_config(cfg: Dict[str, Any]):
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def get_api_key() -> Optional[str]:
    """Get NVIDIA API key from config or environment."""
    cfg = _load_config()
    key = cfg.get("nvidia_api_key") or os.environ.get("NVIDIA_API_KEY")
    return key if key else None


def save_api_key(key: str):
    """Store the NVIDIA API key in project config."""
    cfg = _load_config()
    cfg["nvidia_api_key"] = key
    _save_config(cfg)


class NvidiaGLM47Provider(LLMProvider):
    """GLM-4.7 via NVIDIA Build free API."""

    name = "nvidia_glm47"

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
        return {
            "name": self.name,
            "model": self._model,
            "available": self.is_available(),
            "api_url": NVIDIA_API_URL,
            "rpm_limit": self._rate_limiter.rpm,
            "max_context": DEFAULT_MAX_CONTEXT,
        }

    def send(self, messages: List[Dict[str, str]],
             temperature: float = 0.7,
             max_tokens: int = 16384) -> Dict[str, Any]:
        if not self._api_key:
            return {"ok": False, "text": "",
                    "error": "No NVIDIA API key configured."}

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
            NVIDIA_API_URL, data=data, headers=headers, method="POST"
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
                return {"ok": False, "text": "",
                        "error": f"Rate limited (429). {err_body}"}
            return {"ok": False, "text": "",
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
            "finish_reason": choices[0].get("finish_reason", ""),
        }

    def send_streaming(self, messages: List[Dict[str, str]],
                       temperature: float = 0.7,
                       max_tokens: int = 16384):
        """Generator that yields text chunks from a streaming response."""
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
            NVIDIA_API_URL, data=data, headers=headers, method="POST"
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
