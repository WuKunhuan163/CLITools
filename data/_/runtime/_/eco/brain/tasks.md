# Active Tasks

- [ ] #36: Rate queue manager: integrate with LLM providers
  - Notes: Live test passed: 5/5 tests, parallel calls respect concurrency, 0 rate-limited, key state tracking works
- [ ] #37: Known limitation: file ops viewer data lost on server restart
- [ ] #38: No forced skill pre-scan: add postUserPrompt hook to match prompt against skills
- [ ] #39: No automatic self-test enforcement: add post-write hook to nudge agents to test
- [ ] #40: Context loss on session crash: integrate auto-snapshot into USERINPUT hook chain
- [ ] #41: Cross-session memory is shallow: implement sqlite_fts or hybrid backend for BRAIN recall
- [ ] #42: No tool categorization in TOOL status: add "category" to tool.json, group output
- [ ] #43: IDE-agnostic hook framework: abstract hooks per IDE (VS Code, Windsurf)
- [ ] #44: Procedural triggers not wired to hooks: auto-inject via postToolUse
- [ ] #45: Brain settings UI incomplete: instance creation, blueprint detail, export/import
- [ ] #46: Static file caching: add content-hash query strings for cache invalidation

- [x] #31: Implement before-tool-call hook in base tool with skills matching
- [x] #32: Organize logic/tool/template/ into subdirectories; add report/research/hooks templates
- [x] #33: Fix registry aliases: add version numbers (gemini-2.0 not just gemini)
- [x] #34: Agent capability testing: 5 progressive tasks with GLM 4.7-flash + Auto fallback
- [x] #35: Verify HTML GUI API key save works live for new providers
