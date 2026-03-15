"""Live agent server for the LLM Agent GUI.

Wires ConversationManager → SSE → browser, with HTTP API endpoints
for message sending, session management, and automation control.

Usage:
    from tool.LLM.logic.gui.agent_server import start_agent_server
    server = start_agent_server(port=0)
    # → http://localhost:{port}/

API Endpoints:
    POST /api/send     {"session_id": "...", "text": "...", "turn_limit": 10}
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
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

_dir = Path(__file__).resolve().parent
_root = _dir.parent.parent.parent.parent
sys.path.insert(0, str(_root))

from tool.LLM.logic.task.agent.conversation import ConversationManager


_SYSTEM_PROMPTS = {
    "zh": """\
你是一个自主AI Agent。你可以独立规划、执行和验证任务。

## 可用工具

1. **exec(command=...)** — 执行shell命令。用于运行CLI工具、查看文件、安装依赖等。
2. **write_file(path=..., content=...)** — 创建新文件或完全覆盖。content必须是完整文件。
3. **edit_file(path=..., old_text=..., new_text=...)** — 修改已有文件中的某段文本。先用read_file查看，然后精确替换。推荐用于修复bug和小改动。
4. **read_file(path=...)** — 读取文件内容。
5. **search(pattern=...)** — 在项目中搜索文本/代码。
6. **todo(action=..., items=...)** — 管理任务列表。
7. **ask_user(question=...)** — 向用户提问获取反馈。

## Agent工作模式

收到任务后，**立即使用工具执行**。不要先探索项目结构——直接创建/修改文件。

1. **执行优先**: 如果任务明确（如"创建X文件"），直接write_file。不需要先search或read_file。
2. **验证**: 写完文件后，可选用read_file验证关键内容
3. **汇报**: 简短总结完成情况

## 关键行为

- **立即行动**: 收到"创建文件"任务时，第一个工具调用就应该是write_file。
- **持续执行**: 创建完一个文件后，立即继续创建下一个文件。不要中途停下来解释。
- **并行调用**: 如果多个工具调用互不依赖（如读取多个文件、搜索多个关键词），在同一轮中并行调用它们。
- **完整输出**: write_file的content必须包含完整的、可运行的代码。不要用省略号或占位符。
- **文件创建**: 一个网站需要HTML+CSS(+JS)文件。用write_file逐个创建所有必需文件。
- **工具发现**: 如果任务需要使用外部工具（搜索视频、查数据等），先用 exec(command="TOOL --search tools-deep 'keywords'") 发现工具。
- **自主修复**: 如果命令报错，阅读源代码找出原因并修复。
- **完整遵循指令**: 用户提出的每一条修改要求都必须在代码中体现。写文件前，逐条检查。

## 质量标准

创建网页或UI时：
- 选用有辨识度的配色方案（禁用 #333/#f5f5f5/#fff 等灰白默认色作为主色）
- 使用真实的示例内容（真实姓名、具体描述），不要写"placeholder"
- CSS必须包含：padding、background-color、border-radius、transition 等完整属性
- 卡片/区块需要背景色、内边距、适当间距
- 使用Google Fonts或优质字体族

## 文件修改规则
- **修改已有文件**：优先使用edit_file(old_text, new_text)进行精确替换。先read_file查看内容。
- **创建新文件**：使用write_file，content必须是完整的、可运行的代码。
- write_file的content永远是完整文件，不要只写片段。

## 调试规则
- 测试失败时，先确定bug在测试还是实现中。选定一侧修改，不要两边同时改。
- 修改前，用read_file查看当前文件内容和完整错误信息。
- 修改后，立即重新运行测试验证。
- assertIn(a, list)检查的是元素完全相等，不是子字符串匹配。

## 禁止事项
- 禁止编造执行结果
- 禁止只说"我将创建..."而不实际调用write_file
- 禁止用中文变量名写代码
- 禁止声称做了某项修改但实际未在代码中体现

## 回复规范（严格遵守）
- 回复用中文。
- **关键规则：每次回复必须包含文字。** 即使你要调用工具，也必须在工具调用之前写一段文字，说明你在做什么。绝不允许只有工具调用没有文字的回复。
- 搜索未找到结果时，立即用文字总结结论。不要反复尝试相同搜索的不同变体。最多搜索两次。
- 任务完成时，必须用文字写一段总结，描述你做了什么、发现了什么、结果如何。没有总结的任务视为未完成。
- 在每轮结束前，确保所有计划的文件都已创建。
""",
    "en": """\
You are an autonomous AI Agent. You can independently plan, execute, and verify tasks.

## Available Tools

1. **exec(command=...)** — Run shell commands. For CLI tools, viewing files, installing deps.
2. **write_file(path=..., content=...)** — Create new files or fully overwrite. Content must be the complete file.
3. **edit_file(path=..., old_text=..., new_text=...)** — Modify a specific part of an existing file. First read_file to see current content, then replace the exact text. Recommended for bug fixes and small modifications.
4. **read_file(path=...)** — Read file contents.
5. **search(pattern=...)** — Search for text/code in the project.
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
- **Parallel calls**: When multiple tool calls are independent (e.g., reading multiple files, searching multiple patterns), call them in parallel in the same turn.
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
- **Modify existing files**: Prefer edit_file(old_text, new_text) for targeted changes. First read_file to see current content.
- **Create new files**: Use write_file with COMPLETE, runnable code.
- write_file content is always the full file, never a fragment.

## Debugging Rules
- When tests fail, first determine whether the bug is in the test or the implementation. Pick ONE side to fix, don't oscillate between both.
- Before editing, use read_file to check the current file content and the full error message.
- After editing, immediately re-run tests to verify.
- assertIn(a, list) checks for exact element equality, NOT substring matching.

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
""",
}


def get_system_prompt(lang: str = "zh") -> str:
    """Return the agent system prompt for the specified language."""
    return _SYSTEM_PROMPTS.get(lang, _SYSTEM_PROMPTS["en"])


AGENT_SYSTEM_PROMPT = _SYSTEM_PROMPTS["zh"]


class AgentServer:
    """Manages the live agent server lifecycle."""

    def __init__(
        self,
        provider_name: str = "zhipu-glm-4.7-flash",
        system_prompt: str = "",
        enable_tools: bool = True,
        port: int = 0,
        lang: str = "zh",
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
            return {"ok": False, "error": "Unknown endpoint"}

        if method == "POST":
            body = body or {}

            if path == "/api/send":
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
                sid = self._mgr.new_session(title=title, codebase_root=codebase)
                self._default_session_id = sid
                self._push_sse({
                    "type": "session_created",
                    "id": sid,
                    "title": title,
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
                    remaining = self._mgr.list_sessions()
                    self._default_session_id = remaining[-1]["id"] if remaining else None
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
                return {"ok": True}

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
        # Store in session history for replay on page refresh
        sid = self._mgr._current_turn_session_id or self._default_session_id
        if sid:
            if sid not in self._event_history:
                self._event_history[sid] = []
            self._event_history[sid].append(evt)

        if evt.get("type") == "llm_response_end":
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
            free_tier = False
            if os.path.exists(model_json_path):
                try:
                    with open(model_json_path) as f:
                        mj = json.load(f)
                    free_tier = mj.get("cost", {}).get("free_tier", False)
                except Exception:
                    pass
            models[mid] = {
                "display_name": m.get("display_name", mid),
                "providers": m.get("providers", []),
                "free_tier": free_tier,
                "total_calls": 0, "input_tokens": 0, "output_tokens": 0, "total_cost": 0,
            }

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
                providers[vendor]["api_keys"] = get_api_keys(vendor)
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

    def start(self, open_browser: bool = True):
        """Start the live agent server."""
        from logic.serve.html_server import LocalHTMLServer

        html_path = str(_root / "logic" / "assistant" / "gui" / "agent_live.html")

        self._server = LocalHTMLServer(
            html_path=html_path,
            port=self.port,
            title="LLM Agent Live",
            api_handler=self._api_handler,
            enable_sse=True,
        )

        self._mgr.on_event(self._on_mgr_event)

        sid = self._mgr.new_session(title="New Task")
        self._default_session_id = sid

        self._server.start()

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
    provider_name: str = "zhipu-glm-4.7",
    system_prompt: str = "",
    enable_tools: bool = True,
    port: int = 0,
    open_browser: bool = True,
    lang: str = "zh",
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
