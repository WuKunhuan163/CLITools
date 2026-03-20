# Current Context

**Last updated:** 2026-03-16 23:12
**Working on:** No active task
**Summary:** Testing round 3 complete: 10 tests run, 4 critical bugs fixed (sandbox safe_read bypass, nudge aggressiveness, edit_file write-before-syntax-check, prompt bias). System prompt optimized. All tests pass post-fixes.

## Active Tasks
- [pending] #36: Rate queue manager: integrate with LLM providers
- [pending] #37: Known limitation: file ops viewer data lost on server restart

## Recently Completed
- #31: Implement before-tool-call hook in base tool with skills matching
- #32: Organize logic/tool/template/ into subdirectories; add report/research/hooks templates
- #33: Fix registry aliases: add version numbers (gemini-2.0 not just gemini)
- #34: Agent capability testing: 5 progressive tasks with GLM 4.7-flash + Auto fallback
- #35: Verify HTML GUI API key save works live for new providers

## Recent Activity
- [2026-03-16T14:37] Enhanced project layout mini-map with complete symmetric directory listing: added data/ (API keys, c → for_agent.md, hooks/instance/IDE/Cursor/brain_inject.py, for_agent_reflection.md
- [2026-03-16T18:33] Rewrote Baidu provider (qianfan->OpenAI-compat), added 5 ERNIE models, fixed Gemini validation, adde → tool/LLM/logic/providers/baidu.py, tool/LLM/logic/models/ernie_4_5_turbo_128k/providers/baidu/interface/__init__.py, tool/LLM/logic/registry.py, logic/assistant/gui/server.py, logic/assistant/gui/live.html, tool/LLM/logic/utils/token_counter.py, tool/EXEC/logic/sandbox.py
- [2026-03-16T21:25] Fixed Auto mechanism: (1) Banner now waits for first response token before switching from robot to m
- [2026-03-16T21:30] Auto mechanism test: 12/12 decide OK avg=2.2s (was 14.7s), title avg=1.5s. Fixed rate_queue._load_li
- [2026-03-16T21:52] Live Auto test: 12 rounds completed. Fixed decision prompt to prefer FAST models. Reordered PRIMARY_
- [2026-03-16T22:07] Fixed 3 critical Auto bugs: 1) model_confirmed now delays until actual content (text/reasoning/tool_
- [2026-03-16T22:34] Rate queue gap analysis: RateQueueManager exists in rate_queue.py with full 429 backoff but is NOT w
- [2026-03-16T22:37] Session continuation: completed metacognitive repair expectation RAG arc (for_agent_reflection.md), 
- [2026-03-16T22:41] Fixed: (1) Diff blocks now auto-render via requestIdleCallback instead of requiring click-to-expand.
- [2026-03-16T23:12] Completed comprehensive user testing round 3: 10 tests, found and fixed 4 critical bugs (sandbox saf
