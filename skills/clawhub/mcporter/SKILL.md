---
name: mcporter
title: "Mcporter"
description: "Use the mcporter CLI to list, configure, auth, and call MCP servers/tools directly (HTTP or stdio), including ad-hoc servers, config edits, and CLI/type generation."
source: clawhub
url: https://clawhub.ai/skills/mcporter
imported: 2026-03-17
---

# Mcporter
Use the mcporter CLI to list, configure, auth, and call MCP servers/tools directly (HTTP or stdio), including ad-hoc servers, config edits, and CLI/type generation.
**MIT-0** · Free to use, modify, and redistribute. No attribution required.⭐ 116 ·  39.1k · 1.4k current installs · 1.4k all-time installsbyPeter Steinberger·@steipeteOfficialMIT-0Security ScanVirusTotalVirusTotalSuspicious[View report →](https://www.virustotal.com/gui/file/f9e3e2fae2ff9bb8351d0c46647392d6f923a02b1b531ad7d630b074f5155f38)OpenClawOpenClawSuspiciousmedium confidenceThe SKILL.md aligns with a CLI-focused skill (mcporter) but it contains metadata/install instructions that conflict with the registry record and the runtime instructions allow executing arbitrary stdio commands and storing auth in a local config — review before installing or granting it access.Details ▾ℹPurpose & CapabilityThe skill's name/description are consistent with the SKILL.md: it is a thin wrapper for the mcporter CLI (listing, calling, auth, config, codegen). However the registry metadata provided earlier lists no required binaries or install, while the SKILL.md metadata explicitly requires the 'mcporter' binary and suggests installing the npm package 'mcporter' — an inconsistency between declared registry requirements and the runtime instructions.ℹInstruction ScopeThe instructions confine the agent to using the mcporter CLI (list, call, auth, config, daemon, generate). They do reference a default config path (./config/mcporter.json) and show examples that run arbitrary stdio commands (e.g., `mcporter call --stdio "bun run ./server.ts"`) — which means the CLI can be used to execute or pipe arbitrary subprocess activity. The SKILL.md does not instruct the agent to read unrelated system files or environment variables, but the ability to run arbitrary commands and to perform auth means the agent could cause local execution or create/store credentials.ℹInstall MechanismThe registry claimed 'no install spec', but SKILL.md metadata includes an install hint: a Node/npm package 'mcporter' (kind: node). Installing from npm is common but carries moderate risk compared with no install; npm packages can contain arbitrary code. The install source is a package name (npm-style), not a direct arbitrary URL, which is more traceable, but you should verify the package and its publisher before installing.ℹCredentialsThe skill declares no required environment variables or primary credential. That is proportionate to an instruction-only CLI wrapper. However the SKILL.md documents auth commands and a local config path where credentials (OAuth tokens, API keys) may be stored (./config/mcporter.json by default). Because the skill can run auth flows and write a config file, it may end up storing secrets locally even though none are declared up front — users should be aware and inspect where credentials are kept.✓Persistence & Privilegealways:false and no install-time modifications to other skills are present. The skill does not require permanent platform-wide presence. Note that the skill (like all skills) can be invoked autonomously by the agent (disable-model-invocation:false), so if you permit autonomous use the agent could call mcporter commands without further prompts.What to consider before installingThis skill appears to be a CLI helper for the mcporter tool and is mostly coherent, but pay attention to the following before installing: 1) Metadata mismatch — the registry record shows no install/bin requirements while SKILL.md expects the 'mcporter' binary and offers an npm install; confirm which is accurate. 2) The SKILL.md examples include --stdio and running arbitrary commands (e.g., bun run ./server.ts), so the CLI can be used to execute or proxy arbitrary subprocesses — only allow it in trusted/sandboxed environments. 3) Auth flows will likely store tokens in a local config (./config/mcporter.json) — inspect and lock that file and avoid giving broad platform credentials. 4) The install suggestion is an npm package; review the npm package page, author, source repo, and recent releases before installing. 5) If you allow the agent to invoke this skill autonomously, consider restricting what credentials the agent has access to and test the CLI manually first to understand its behavior.Like a lobster shell, security has layers — review code before you run it.
Current version**v1.0.0**Download ziplatestvk973778pzgzetvsttxj3kqw05n7ykngf
### License
MIT-0Free to use, modify, and redistribute. No attribution required.**Terms**[https://spdx.org/licenses/MIT-0.html](https://spdx.org/licenses/MIT-0.html)
### Runtime requirements
📦 Clawdis**Bins**mcporter
### Install
**Install mcporter (node)**Bins: mcporter`npm i -g mcporter`FilesCompareVersions
## SKILL.md

# mcporter

Use `mcporter` to work with MCP servers directly.

Quick start

- `mcporter list`
- `mcporter list <server> --schema`
- `mcporter call <server.tool> key=value`

Call tools

- Selector: `mcporter call linear.list_issues team=ENG limit:5`
- Function syntax: `mcporter call "linear.create_issue(title: \"Bug\")"`
- Full URL: `mcporter call https://api.example.com/mcp.fetch url:https://example.com`
- Stdio: `mcporter call --stdio "bun run ./server.ts" scrape url=https://example.com`
- JSON payload: `mcporter call <server.tool> --args '{"limit":5}'`

Auth + config

- OAuth: `mcporter auth <server | url> [--reset]`
- Config: `mcporter config list|get|add|remove|import|login|logout`

Daemon

- `mcporter daemon start|status|stop|restart`

Codegen

- CLI: `mcporter generate-cli --server <name>` or `--command <url>`
- Inspect: `mcporter inspect-cli <path> [--json]`
- TS: `mcporter emit-ts <server> --mode client|types`

Notes

- Config default: `./config/mcporter.json` (override with `--config`).
- Prefer `--output json` for machine-readable results.

### Files
1 totalSKILL.md1.4 KBSelect a fileSelect a file to preview.
## Comments
Loading comments…