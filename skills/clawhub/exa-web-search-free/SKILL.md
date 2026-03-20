---
name: exa-web-search-free
title: "Exa Web Search (Free)"
description: "Free AI search via Exa MCP. Web search for news/info, code search for docs/examples from GitHub/StackOverflow, company research for business intel. No API key needed."
source: clawhub
url: https://clawhub.ai/skills/exa-web-search-free
imported: 2026-03-17
---

# Exa Web Search (Free)
Free AI search via Exa MCP. Web search for news/info, code search for docs/examples from GitHub/StackOverflow, company research for business intel. No API key needed.
**MIT-0** · Free to use, modify, and redistribute. No attribution required.⭐ 58 ·  17.1k · 146 current installs · 154 all-time installsbyStavan·@Whiteknight07MIT-0Security ScanVirusTotalVirusTotalBenign[View report →](https://www.virustotal.com/gui/file/df01a8cfb4ac8a01040e29a032ef33fff862c7539aac98d86cacd3d807d9e843)OpenClawOpenClawSuspiciousmedium confidenceThe skill is coherent in offering web/code/company search via a third‑party MCP service, but the runtime instructions require an external mcporter CLI and will send arbitrary queries to https://mcp.exa.ai — a potential data‑leak/privacy risk — and the registry metadata and SKILL.md disagree about required binaries.Details ▾!Purpose & CapabilityThe skill's stated purpose (web/code/company search via Exa MCP) matches the instructions which call a remote MCP service. However SKILL.md metadata declares a required binary 'mcporter' while the registry's top-level requirements list 'none' for required binaries — an inconsistency. Requesting mcporter is reasonable for this purpose, but the registry should declare it.!Instruction ScopeRuntime instructions tell the agent to run mcporter commands that configure and call a remote endpoint (https://mcp.exa.ai/mcp) and to enable optional tools (crawling, people search, deep researcher). Those commands will transmit user queries (and any data included in them) to an external service. The instructions do not limit or warn about sending sensitive data, nor do they require any local validation of results. Crawling and people-search features can retrieve or expose PII and arbitrary web content.ℹInstall MechanismNo install spec or code files are provided (instruction-only), so nothing is written to disk by the skill itself. Risk arises from reliance on an external binary (mcporter) and network calls to the MCP endpoint rather than from an installation step. The skill references GitHub/npm resources for Exa MCP which are plausible but unverified here.ℹCredentialsThe skill declares no required environment variables or credentials, which is consistent with 'No API key needed.' However, because queries are sent to a third party, this design means user prompts and any embedded secrets could be leaked to that external service. No provision is made to prevent accidental transmission of sensitive data.ℹPersistence & Privilegealways:false (normal). The skill can be invoked autonomously (platform default). Combined with the optional 'deep_researcher' and crawling/people-search tools, autonomous invocation increases the amount of data that could be sent externally if allowed — but autonomous invocation alone is not unusual.What to consider before installingBefore installing, consider: (1) The skill expects you to have the mcporter CLI and will configure and call a remote service (mcp.exa.ai). Verify you trust that domain and the mcporter binary (inspect its source or installed package). (2) Do not send secrets or private data in queries — the skill will forward whatever you ask to an external service. (3) The registry metadata omitted the required 'mcporter' binary — ask the publisher to correct this. (4) If you need stricter control, only enable the skill as user‑invocable (avoid autonomous runs), and test with non‑sensitive queries first. (5) If you require assurance, review the referenced GitHub/npm projects (exa-mcp-server) and any privacy/security docs for mcp.exa.ai before using.Like a lobster shell, security has layers — review code before you run it.
Current version**v1.0.1**Download ziplatestvk97ebq12325t607ehmztep31zn802y8c
### License
MIT-0Free to use, modify, and redistribute. No attribution required.**Terms**[https://spdx.org/licenses/MIT-0.html](https://spdx.org/licenses/MIT-0.html)
### Runtime requirements
🔍 Clawdis**Bins**mcporterFilesCompareVersions
## SKILL.md

# Exa Web Search (Free)

Neural search for web, code, and company research. No API key required.

## Setup

Verify mcporter is configured:

```bash
mcporter list exa

```

If not listed:

```bash
mcporter config add exa https://mcp.exa.ai/mcp

```

## Core Tools

### web_search_exa

Search web for current info, news, or facts.

```bash
mcporter call 'exa.web_search_exa(query: "latest AI news 2026", numResults: 5)'

```

**Parameters:**

- `query` - Search query
- `numResults` (optional, default: 8)
- `type` (optional) - `"auto"`, `"fast"`, or `"deep"`

### get_code_context_exa

Find code examples and docs from GitHub, Stack Overflow.

```bash
mcporter call 'exa.get_code_context_exa(query: "React hooks examples", tokensNum: 3000)'

```

**Parameters:**

- `query` - Code/API search query
- `tokensNum` (optional, default: 5000) - Range: 1000-50000

### company_research_exa

Research companies for business info and news.

```bash
mcporter call 'exa.company_research_exa(companyName: "Anthropic", numResults: 3)'

```

**Parameters:**

- `companyName` - Company name
- `numResults` (optional, default: 5)

## Advanced Tools (Optional)

Six additional tools available by updating config URL:

- `web_search_advanced_exa` - Domain/date filters
- `deep_search_exa` - Query expansion
- `crawling_exa` - Full page extraction
- `people_search_exa` - Professional profiles
- `deep_researcher_start/check` - AI research agent

**Enable all tools:**

```bash
mcporter config add exa-full "https://mcp.exa.ai/mcp?tools=web_search_exa,web_search_advanced_exa,get_code_context_exa,deep_search_exa,crawling_exa,company_research_exa,people_search_exa,deep_researcher_start,deep_researcher_check"

# Then use:
mcporter call 'exa-full.deep_search_exa(query: "AI safety research")'

```

## Tips

- Web: Use `type: "fast"` for quick lookup, `"deep"` for thorough research
- Code: Lower `tokensNum` (1000-2000) for focused, higher (5000+) for comprehensive
- See [examples.md](references/examples.md) for more patterns

## Resources

- [GitHub](https://github.com/exa-labs/exa-mcp-server)
- [npm](https://www.npmjs.com/package/exa-mcp-server)
- [Docs](https://exa.ai/docs)

### Files
2 totalSKILL.md2.4 KBreferences/examples.md4.6 KBSelect a fileSelect a file to preview.
## Comments
Loading comments…