"""Live agent server for the LLM Agent GUI.

Wires ConversationManager → SSE → browser, with HTTP API endpoints
for message sending, session management, and automation control.

Usage:
    from tool.LLM.logic.gui.agent_server import start_agent_server
    server = start_agent_server(port=0)
    # → http://localhost:{port}/

API Endpoints:
    POST /api/send     {"session_id": "...", "text": "...", "turn_limit": 20}
    POST /api/model    {"model": "zhipu-glm-4.7-flash"}
    POST /api/session  {"title": "..."}
    POST /api/rename   {"session_id": "...", "title": "..."}
    POST /api/delete   {"session_id": "..."}
    GET  /api/sessions
    GET  /api/state
    GET  /api/usage
    POST /api/input    {"session_id": "...", "text": "..."}
                       Simulates typing into the input box then clicking send.
                       The browser receives an 'inject_input' SSE event to
                       animate the text appearing, then auto-submits.
    POST /api/inject_event   {"session_id": "...", "event": {...}}
                             Push a single event into the SSE stream + history.
    POST /api/inject_events  {"session_id": "...", "events": [{...}, ...]}
                             Push multiple events in order.
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

_dir = Path(__file__).resolve().parent
_root = _dir.parent.parent.parent.parent
sys.path.insert(0, str(_root))

from tool.LLM.logic.gui.round_store import (
    RoundStore, render_token_page, render_read_page,
    render_edit_page, _not_found_page
)

from tool.LLM.logic.task.agent.conversation import ConversationManager


_SYSTEM_PROMPT = """\
You are an autonomous AI Agent. You can independently plan, execute, and verify tasks.

## Available Tools

1. **exec(command=...)** — Run shell commands. For CLI tools, viewing files, installing deps.
2. **write_file(path=..., content=...)** — Create new files or fully overwrite. Content must be the complete file.
3. **edit_file(path=..., old_text=..., new_text=...)** — Modify a specific part of an existing file. First read_file to see current content, then replace the exact text. Recommended for bug fixes and small modifications.
4. **read_file(path=...)** — Read ONE file's contents. Path must be a specific file path (e.g. "tool/LLM/logic/utils/token_counter.py"), NOT a directory. Use search() first to locate relevant code ranges.
5. **search(pattern=..., path=...)** — Search for text INSIDE files (grep-style). NOT for listing files. To list files, use exec(command="find <dir> -name '*.py'").
6. **todo(action=..., items=...)** — Manage a task list.
7. **ask_user(question=...)** — Ask the user a question for feedback.

## Agent Workflow

When receiving a task, **use tools immediately**. Do NOT explore the project first — go straight to creating/modifying files.

1. **Act first**: If the task is clear (e.g., "create X file"), call write_file immediately.
2. **Verify**: Optionally use read_file to confirm key content after writing
3. **Report**: Briefly summarize what was done

## Key Behaviors

- **Act immediately**: When asked to "create a file", your FIRST tool call should be write_file.
- **Continuous execution**: After creating one file, immediately create the next. Don't stop to explain mid-way.
- **One call at a time**: Each tool call takes exactly ONE set of arguments. To read multiple files, call read_file separately for each file.
- **Complete output**: write_file content must contain complete, runnable code. No ellipsis or placeholders.
- **File creation**: A website needs HTML+CSS(+JS) files. Use write_file to create all required files.
- **Tool discovery**: If the task requires external tools (search videos, fetch data), first use exec(command="TOOL --search tools-deep 'keywords'") to discover tools.
- **Self-repair**: If a command errors, read the source code to find the cause and fix it.
- **Follow ALL instructions**: Every specific change the user requests MUST appear in the written code. Before writing, mentally check each request.

## Quality Standards

When creating web pages or UI:
- Use a distinctive color palette (NEVER use #333/#f5f5f5/#fff as primary colors)
- Use realistic sample content (real names, specific descriptions), never "placeholder" text
- CSS must include complete properties: padding, background-color, border-radius, transition
- Cards/sections need background colors, inner padding, and proper spacing
- Use Google Fonts or a quality font stack

When writing code:
- Include proper error handling
- Use meaningful variable names
- Add necessary imports

## File Modification Rules
- **Modify existing files**: Prefer edit_file(old_text, new_text) for targeted changes. First read_file to see current content, then copy the exact snippet to modify as old_text.
- **Create new files**: Use write_file with COMPLETE, runnable code.
- write_file content is always the full file, never a fragment.
- **Large files**: If read_file is truncated, use start_line/end_line params to read specific sections. Do NOT re-read the same file repeatedly.

### edit_file Example
If the file contains:
```python
def hello():
    print("hello")
```
To add a parameter: edit_file(path="file.py", old_text='def hello():\\n    print("hello")', new_text='def hello(name):\\n    print(f"hello {name}")')
To append a new function: edit_file(path="file.py", old_text='    print("hello")', new_text='    print("hello")\\n\\ndef goodbye():\\n    print("bye")')

## Debugging Rules
- When tests fail, first determine whether the bug is in the test or the implementation. Pick ONE side to fix, don't oscillate between both.
- Before editing, use read_file to check the current file content and the full error message.
- After editing, immediately re-run tests to verify.
- assertIn(a, list) checks for exact element equality, NOT substring matching.

## Test Writing Rules
- Test expected values must exactly match the tool's documented behavior. If a tool is case-sensitive by default, test expectations must also be case-sensitive.
- `"".split("\n")` produces `[""]` (length 1), not `[]`. To check empty output, use `stdout.strip() == ""` instead of `len(lines) == 0`.
- Before writing a test, mentally simulate the tool's exact output for the test input. Verify character-by-character. Never assume.
- If a test fails for 2+ rounds, check whether the test's expected values are reasonable FIRST, then check the implementation.

## Handling User Corrections
- When the user gives specific fix instructions (e.g., "change X to Y"), **execute immediately**. Do NOT re-analyze the project.
- Every round MUST include at least one write/edit/exec action. Do NOT spend multiple rounds only reading files.
- If the user says "the test is unreasonable", fix the test directly. Do NOT try to fix the implementation to match unreasonable tests.

## Forbidden
- Never fabricate execution results
- Never say "I will create..." without actually calling write_file
- Never use non-ASCII variable names in code
- Never claim you made a change that is not actually in the written code

## Response Guidelines (STRICT)
- Reply in English.
- **KEY RULE: Every response MUST contain text.** Even when making tool calls, you MUST write explanatory text BEFORE the tool call. Responses that contain only tool calls with no text are forbidden.
- If a search finds no results, immediately state your conclusion in text. Do NOT keep trying different variations. Maximum 2 search attempts.
- When your task is complete, you MUST write a text summary describing what you did, what you found, and the outcome. A task without a summary is considered incomplete.
- Before ending your turn, ensure ALL planned files have been created.
"""


def get_system_prompt(lang: str = "en") -> str:
    """Return the agent system prompt."""
    return _SYSTEM_PROMPT


AGENT_SYSTEM_PROMPT = _SYSTEM_PROMPT


class AgentServer:
    """Manages the live agent server lifecycle."""

    def __init__(
        self,
        provider_name: str = "zhipu-glm-4.7-flash",
        system_prompt: str = "",
        enable_tools: bool = True,
        port: int = 0,
        lang: str = "en",
        default_codebase: str = None,
        brain=None,
    ):
        self.provider_name = provider_name
        self.system_prompt = system_prompt or get_system_prompt(lang)
        self.enable_tools = enable_tools
        self.port = port
        self.lang = lang
        self.default_codebase = default_codebase

        self._mgr = ConversationManager(
            provider_name=provider_name,
            system_prompt=self.system_prompt,
            enable_tools=enable_tools,
            default_codebase=default_codebase,
            brain=brain,
        )
        self._server = None
        self._default_session_id = None
        self._usage_calls = []
        self._event_history: Dict[str, list] = {}  # session_id -> [events]
        self._round_store = RoundStore()
        self._mgr._event_provider = lambda sid: self._event_history.get(sid, [])
        self._mgr._round_store = self._round_store
        self._load_persisted_events()

    def _load_persisted_events(self):
        """Load event history from persisted session files.

        Supports both new layout (``<id>/history.json``) and legacy (``<id>.json``).
        """
        import glob
        sessions_dir = os.path.join(str(_root), "runtime", "sessions")
        if not os.path.isdir(sessions_dir):
            return
        for path in glob.glob(os.path.join(sessions_dir, "*/history.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                sid = data.get("id")
                events = data.get("events", [])
                if sid and events:
                    self._event_history[sid] = events
            except Exception:
                continue
        for path in glob.glob(os.path.join(sessions_dir, "*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                sid = data.get("id")
                if sid and sid not in self._event_history:
                    events = data.get("events", [])
                    if events:
                        self._event_history[sid] = events
            except Exception:
                continue

    def _api_handler(self, method: str, path: str, body: Optional[dict]) -> dict:
        """Route API requests to ConversationManager methods."""
        path = path.split("?")[0]

        if method == "GET":
            if path == "/api/sessions":
                return {"ok": True, "sessions": self._mgr.list_sessions()}
            elif path == "/api/state":
                return {"ok": True, "state": self._mgr.get_state()}
            elif path == "/api/usage":
                return {"ok": True, "usage": self._get_usage_data()}
            elif path.startswith("/api/history/"):
                sid = path.split("/api/history/")[1].strip("/")
                events = self._event_history.get(sid, [])
                return {"ok": True, "events": events}
            elif path == "/api/configured_models":
                return self._get_configured_models()
            elif path == "/api/session_config":
                return self._get_session_config()
            return {"ok": False, "error": "Unknown endpoint"}

        if method == "POST":
            body = body or {}

            if path == "/api/send":
                if body.get("_config"):
                    return self._save_session_config(body.get("key"), body.get("value"))
                sid = body.get("session_id") or self._default_session_id
                text = body.get("text", "").strip()
                if not sid:
                    return {"ok": False, "error": "No active session"}
                if not text:
                    return {"ok": False, "error": "Empty message"}
                session = self._mgr.get_session(sid)
                if not session:
                    return {"ok": False, "error": f"Session {sid} not found"}
                context_feed = body.get("context_feed")
                turn_limit = int(body.get("turn_limit", 0))
                self._mgr.send_message(sid, text, blocking=False,
                                       context_feed=context_feed,
                                       turn_limit=turn_limit)
                return {"ok": True, "session_id": sid}

            elif path == "/api/input":
                sid = body.get("session_id") or self._default_session_id
                text = body.get("text", "").strip()
                if not sid or not text:
                    return {"ok": False, "error": "Missing session_id or text"}
                self._push_sse({
                    "type": "inject_input",
                    "session_id": sid,
                    "text": text,
                })
                return {"ok": True, "session_id": sid}

            elif path == "/api/model":
                model = body.get("model", "").strip()
                if not model:
                    return {"ok": False, "error": "Missing model"}
                try:
                    from tool.LLM.logic.registry import get_provider
                    provider = get_provider(model)
                    if not provider.is_available():
                        return {"ok": False, "error": f"Model {model} is not available"}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
                old_model = self._mgr._provider_name
                self._mgr._provider_name = model
                self.provider_name = model
                self._push_sse({
                    "type": "model_switched",
                    "from": old_model,
                    "to": model,
                })
                return {"ok": True, "model": model}

            elif path == "/api/session":
                title = body.get("title", "New Task")
                codebase = body.get("codebase_root")
                mode = body.get("mode", "agent")
                sid = self._mgr.new_session(
                    title=title, codebase_root=codebase, mode=mode)
                self._default_session_id = sid

                pre_events = body.get("events", [])
                if pre_events:
                    if sid not in self._event_history:
                        self._event_history[sid] = []
                    for evt in pre_events:
                        evt["session_id"] = sid
                        for k, v in list(evt.items()):
                            if v == "__SID__":
                                evt[k] = sid
                        self._event_history[sid].append(evt)

                self._push_sse({
                    "type": "session_created",
                    "id": sid,
                    "title": title,
                    "mode": mode,
                })
                return {"ok": True, "session_id": sid}

            elif path == "/api/rename":
                sid = body.get("session_id", "")
                title = body.get("title", "")
                if sid and title:
                    self._mgr.rename_session(sid, title)
                    return {"ok": True}
                return {"ok": False, "error": "Missing session_id or title"}

            elif path == "/api/delete":
                sid = body.get("session_id", "")
                if sid:
                    self._mgr.delete_session(sid)
                    if sid in self._event_history:
                        del self._event_history[sid]
                    remaining = self._mgr.list_sessions()
                    self._default_session_id = remaining[-1]["id"] if remaining else None
                    self._push_sse({"type": "session_deleted", "id": sid})
                    return {"ok": True}
                return {"ok": False, "error": "Missing session_id"}

            elif path == "/api/cancel":
                self._mgr.cancel_current()
                return {"ok": True}

            elif path == "/api/validate-key":
                vendor = body.get("vendor", "").strip()
                key = body.get("key", "").strip()
                if not vendor or not key:
                    return {"ok": False, "error": "Missing vendor or key"}
                return self._validate_api_key(vendor, key)

            elif path == "/api/save-key":
                vendor = body.get("vendor", "").strip()
                key = body.get("key", "").strip()
                if not vendor or not key:
                    return {"ok": False, "error": "Missing vendor or key"}
                from tool.LLM.logic.config import set_config_value
                set_config_value(f"{vendor}_api_key", key)
                self._push_sse({"type": "settings_changed", "action": "key_saved", "vendor": vendor})
                return {"ok": True}

            elif path == "/api/delete-key":
                vendor = body.get("vendor", "").strip()
                if not vendor:
                    return {"ok": False, "error": "Missing vendor"}
                from tool.LLM.logic.config import set_config_value
                set_config_value(f"{vendor}_api_key", "")
                self._push_sse({"type": "settings_changed", "action": "key_deleted", "vendor": vendor})
                return {"ok": True}

            elif path == "/api/revert-hunk":
                return self._revert_hunk(body)

            elif path == "/api/queue":
                sid = body.get("session_id") or self._default_session_id
                action = body.get("action", "list")
                if not sid:
                    return {"ok": False, "error": "No active session"}
                if action == "list":
                    queue = self._mgr.get_task_queue(sid)
                    return {"ok": True, "queue": [
                        {"text": t.get("text", "")[:100]} for t in queue
                    ]}
                elif action == "clear":
                    count = self._mgr.clear_task_queue(sid)
                    return {"ok": True, "cleared": count}
                return {"ok": False, "error": f"Unknown queue action: {action}"}

            elif path == "/api/inject_event":
                sid = body.get("session_id") or self._default_session_id
                event = body.get("event")
                if not sid:
                    return {"ok": False, "error": "No active session"}
                if not event or not isinstance(event, dict):
                    return {"ok": False, "error": "Missing or invalid event"}
                event["session_id"] = sid
                if sid not in self._event_history:
                    self._event_history[sid] = []
                self._event_history[sid].append(event)
                self._push_sse(event)
                return {"ok": True}

            elif path == "/api/inject_events":
                sid = body.get("session_id") or self._default_session_id
                events = body.get("events", [])
                if not sid:
                    return {"ok": False, "error": "No active session"}
                if not isinstance(events, list):
                    return {"ok": False, "error": "events must be a list"}
                if sid not in self._event_history:
                    self._event_history[sid] = []
                for evt in events:
                    if isinstance(evt, dict):
                        evt["session_id"] = sid
                        self._event_history[sid].append(evt)
                        self._push_sse(evt)
                return {"ok": True, "count": len(events)}

            return {"ok": False, "error": "Unknown endpoint"}

        return {"ok": False, "error": "Method not allowed"}

    @staticmethod
    def _validate_api_key(vendor: str, key: str) -> dict:
        """Validate an API key by making a minimal test request."""
        VENDOR_PROVIDERS = {
            "zhipu": "zhipu-glm-4.7-flash",
            "google": "google-gemini-2.0-flash",
            "baidu": "baidu-ernie-speed-8k",
            "tencent": "tencent-hunyuan-lite",
            "siliconflow": "siliconflow-qwen2.5-7b",
            "nvidia": "nvidia-glm-4-7b",
        }
        provider_name = VENDOR_PROVIDERS.get(vendor)
        if not provider_name:
            return {"ok": False, "error": f"Unknown vendor: {vendor}"}
        try:
            from tool.LLM.logic.registry import get_provider
            provider = get_provider(provider_name, api_key=key)
            result = provider._send_request(
                [{"role": "user", "content": "hi"}],
                temperature=0.1, max_tokens=5)
            if result.get("ok"):
                return {"ok": True, "model": result.get("model", provider_name)}
            return {"ok": False, "error": result.get("error", "Validation failed")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _push_sse(self, evt: dict):
        if self._server:
            self._server.push_event(evt)

    def _on_mgr_event(self, evt: dict):
        """Forward ConversationManager events to SSE, track usage, and store history."""
        sid = self._mgr._current_turn_session_id or self._default_session_id
        if sid:
            evt["session_id"] = sid
            if sid not in self._event_history:
                self._event_history[sid] = []
            self._event_history[sid].append(evt)

        if evt.get("type") == "llm_response_end":
            round_num = evt.get("round", 0)
            if sid and round_num:
                session = self._mgr.get_session(sid)
                ctx_msgs = session.context.messages if session else []
                self._round_store.record_round(
                    sid, round_num,
                    input_tokens=json.dumps(ctx_msgs[-20:], ensure_ascii=False, indent=1) if ctx_msgs else "",
                    output_tokens=evt.get("_full_text", ""),
                    context_messages=ctx_msgs,
                )

            import time
            self._usage_calls.append({
                "timestamp": time.time(),
                "model": evt.get("model", self.provider_name),
                "provider": evt.get("provider", self.provider_name),
                "input_tokens": evt.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": evt.get("usage", {}).get("completion_tokens", 0),
                "latency_s": evt.get("latency_s", 0),
                "ok": not evt.get("error"),
            })
        self._push_sse(evt)

    def _get_configured_models(self) -> dict:
        """Return models that have at least one configured+available provider."""
        try:
            from tool.LLM.logic.registry import list_models, list_providers as list_reg_providers
            available_providers = set()
            for p in list_reg_providers():
                if p.get("available"):
                    available_providers.add(p.get("name", ""))

            configured = [{"value": "auto", "label": "Auto"}]
            for m in list_models():
                mid = m["model"]
                provs = m.get("providers", [])
                if any(p in available_providers for p in provs):
                    configured.append({
                        "value": mid,
                        "label": m.get("display_name", mid),
                    })
            return {"ok": True, "models": configured}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _revert_hunk(self, body: dict) -> dict:
        """Revert a single diff hunk by applying the inverse edit."""
        path = body.get("path", "").strip()
        old_text = body.get("old_text", "")
        new_text = body.get("new_text", "")

        if not path:
            return {"ok": False, "error": "Missing path"}

        import os
        if not os.path.isabs(path):
            cwd = self._mgr._get_cwd() if hasattr(self._mgr, '_get_cwd') else os.getcwd()
            path = os.path.join(cwd, path)

        try:
            content = open(path, encoding='utf-8', errors='replace').read()
            if old_text and old_text in content:
                new_content = content.replace(old_text, new_text, 1)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return {"ok": True, "path": path}
            elif not old_text and new_text:
                return {"ok": False, "error": "Cannot revert: added text not found in file"}
            else:
                return {"ok": False, "error": "Text to revert not found in file"}
        except FileNotFoundError:
            return {"ok": False, "error": f"File not found: {path}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _save_session_config(self, key, value) -> dict:
        """Save a single session config key from the frontend settings panel."""
        if not key:
            return {"ok": False, "error": "Missing key"}
        try:
            from tool.LLM.logic.config import load_config, save_config
            cfg = load_config()
            try:
                value = int(value)
            except (ValueError, TypeError):
                pass
            cfg[key] = value
            save_config(cfg)
            return {"ok": True, "key": key, "value": value}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get_session_config(self) -> dict:
        """Return session configuration defaults from the LLM config store."""
        try:
            from tool.LLM.logic.config import get_config_value
            SESSION_DEFAULTS = {
                "default_turn_limit": 20,
                "max_input_tokens": 65536,
                "max_output_tokens": 16384,
                "max_context_tokens": 1048576,
                "max_read_chars": 12000,
                "max_exec_chars": 6000,
                "history_limit": 20,
            }
            config = {}
            for key, default in SESSION_DEFAULTS.items():
                val = get_config_value(key, default)
                try:
                    config[key] = int(val)
                except (ValueError, TypeError):
                    config[key] = default
            return {"ok": True, "config": config}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get_usage_data(self) -> dict:
        """Aggregate usage data for Settings panel."""
        models = {}
        providers = {}
        from tool.LLM.logic.registry import list_models, list_providers as list_reg_providers
        from tool.LLM.logic.config import get_api_keys

        for m in list_models():
            mid = m["model"]
            cap = m.get("capabilities", {})
            model_json_path = os.path.join(
                os.path.dirname(__file__), "..", "models",
                mid.replace("-", "_").replace(".", "_"), "model.json")
            cost_info = {}
            bench_info = {}
            free_tier = False
            if os.path.exists(model_json_path):
                try:
                    with open(model_json_path) as f:
                        mj = json.load(f)
                    cost_info = mj.get("cost", {})
                    bench_info = mj.get("benchmarks", {})
                    free_tier = cost_info.get("free_tier", False)
                except Exception:
                    pass
            models[mid] = {
                "display_name": m.get("display_name", mid),
                "providers": m.get("providers", []),
                "free_tier": free_tier,
                "input_price": cost_info.get("input_per_1m", cost_info.get("input_per_1k", 0) * 1000),
                "output_price": cost_info.get("output_per_1m", cost_info.get("output_per_1k", 0) * 1000),
                "currency": cost_info.get("currency", "USD"),
                "benchmarks": bench_info,
                "total_calls": 0, "input_tokens": 0, "output_tokens": 0, "total_cost": 0,
            }

        available_providers = set()
        for p in list_reg_providers():
            pname = p.get("name", "")
            vendor = pname.split("-")[0] if pname else "unknown"
            if vendor not in providers:
                providers[vendor] = {
                    "models": [], "total_calls": 0,
                    "input_tokens": 0, "output_tokens": 0, "total_cost": 0,
                    "api_keys": [],
                }
            if pname not in providers[vendor]["models"]:
                providers[vendor]["models"].append(pname)
            try:
                keys = get_api_keys(vendor)
                providers[vendor]["api_keys"] = keys
                if keys:
                    available_providers.add(pname)
                    providers[vendor]["configured"] = True
            except Exception:
                pass

        for mid, mdata in models.items():
            mdata["configured"] = any(p in available_providers for p in mdata.get("providers", []))
            mdata["configured_providers"] = [p for p in mdata.get("providers", []) if p in available_providers]

        try:
            from tool.ARTIFICIAL_ANALYSIS.interface import get_rankings
            model_slugs = list(models.keys())
            aa_data = get_rankings(model_slugs)
            for our_slug, aa in aa_data.items():
                for mid in models:
                    if our_slug.lower() in mid.lower() or mid.lower() in our_slug.lower():
                        evals = aa.get("evaluations", {})
                        rankings = aa.get("rankings", {})
                        models[mid]["aa_benchmarks"] = {
                            "intelligence": evals.get("artificial_analysis_intelligence_index"),
                            "coding": evals.get("artificial_analysis_coding_index"),
                            "math": evals.get("artificial_analysis_math_index"),
                            "speed_tps": aa.get("speed"),
                            "ttft_s": aa.get("ttft"),
                        }
                        models[mid]["aa_rankings"] = rankings
                        break
        except Exception:
            pass

        for call in self._usage_calls:
            model_key = call.get("model", "")
            prov_key = call.get("provider", "")
            vendor = prov_key.split("-")[0] if prov_key else "unknown"
            inp = call.get("input_tokens", 0)
            outp = call.get("output_tokens", 0)

            for mid, mdata in models.items():
                if mid in model_key or model_key in mdata.get("providers", []):
                    mdata["total_calls"] += 1
                    mdata["input_tokens"] += inp
                    mdata["output_tokens"] += outp
                    break

            if vendor in providers:
                providers[vendor]["total_calls"] += 1
                providers[vendor]["input_tokens"] += inp
                providers[vendor]["output_tokens"] += outp

        return {"models": models, "providers": providers, "calls": self._usage_calls[-100:]}

    def _page_handler(self, path: str) -> Optional[str]:
        """Handle /session/<sid>/<type>/<round_id>/... page routes."""
        qs = ""
        if "?" in path:
            path, qs = path.split("?", 1)
        parts = path.strip("/").split("/")
        if len(parts) < 4 or parts[0] != "session":
            return _not_found_page("Invalid path")
        sid = parts[1]
        data_type = parts[2]
        try:
            round_num = int(parts[3])
        except (ValueError, IndexError):
            return _not_found_page("Invalid round number")

        if data_type in ("input", "output", "context"):
            content = self._round_store.get_token_data(sid, round_num, data_type)
            token_count = 0
            cost = 0.0
            for param in qs.split("&"):
                if param.startswith("tokens="):
                    try: token_count = int(param.split("=")[1])
                    except ValueError: pass
                elif param.startswith("cost="):
                    try: cost = float(param.split("=")[1])
                    except ValueError: pass
            return render_token_page(sid, round_num, data_type, content,
                                     token_count=token_count, cost=cost)
        elif data_type == "read":
            rel_path = "/".join(parts[4:-1]) if len(parts) > 5 else (parts[4] if len(parts) > 4 else "")
            op_id = 0
            if len(parts) > 5:
                try:
                    op_id = int(parts[-1])
                except ValueError:
                    rel_path = "/".join(parts[4:])
            op = self._round_store.get_file_op(sid, round_num, "read", rel_path, op_id)
            if not op:
                return _not_found_page(f"No read data for {rel_path} in round {round_num}")
            return render_read_page(sid, round_num, op)
        elif data_type == "edit":
            rel_path = "/".join(parts[4:-1]) if len(parts) > 5 else (parts[4] if len(parts) > 4 else "")
            op_id = 0
            if len(parts) > 5:
                try:
                    op_id = int(parts[-1])
                except ValueError:
                    rel_path = "/".join(parts[4:])
            op = self._round_store.get_file_op(sid, round_num, "edit", rel_path, op_id)
            if not op:
                return _not_found_page(f"No edit data for {rel_path} in round {round_num}")
            return render_edit_page(sid, round_num, op)
        else:
            return _not_found_page(f"Unknown data type: {data_type}")

    def start(self, open_browser: bool = True):
        """Start the live agent server."""
        from logic.serve.html_server import LocalHTMLServer

        html_path = str(_root / "logic" / "assistant" / "gui" / "agent_live.html")

        self._server = LocalHTMLServer(
            html_path=html_path,
            port=self.port,
            title="LLM Agent Live",
            api_handler=self._api_handler,
            page_handler=self._page_handler,
            enable_sse=True,
        )

        self._mgr.on_event(self._on_mgr_event)

        existing = self._mgr.list_sessions()
        if existing:
            self._default_session_id = existing[0]["id"]
        else:
            sid = self._mgr.new_session(title="New Task")
            self._default_session_id = sid

        self._server.start()
        self.port = self._server.port

        if open_browser:
            self._server.open_browser()

        return self._server

    def stop(self):
        if self._server:
            self._server.stop()

    @property
    def url(self) -> str:
        return self._server.url if self._server else ""

    @property
    def default_session_id(self) -> Optional[str]:
        return self._default_session_id


def start_agent_server(
    provider_name: str = "zhipu-glm-4.7-flash",
    system_prompt: str = "",
    enable_tools: bool = True,
    port: int = 0,
    open_browser: bool = True,
    lang: str = "en",
    default_codebase: str = None,
    brain=None,
) -> AgentServer:
    """Convenience function to start the live agent server.

    Returns the AgentServer instance (server is already running).
    """
    agent = AgentServer(
        provider_name=provider_name,
        system_prompt=system_prompt,
        enable_tools=enable_tools,
        port=port,
        lang=lang,
        default_codebase=default_codebase,
        brain=brain,
    )
    agent.start(open_browser=open_browser)
    return agent
