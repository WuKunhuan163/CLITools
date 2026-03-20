---
name: playwright-mcp
title: "Playwright MCP"
description: "Browser automation via Playwright MCP server. Navigate websites, click elements, fill forms, extract data, take screenshots, and perform full browser automation workflows."
source: clawhub
url: https://clawhub.ai/skills/playwright-mcp
imported: 2026-03-17
---

# Playwright MCP
Browser automation via Playwright MCP server. Navigate websites, click elements, fill forms, extract data, take screenshots, and perform full browser automation workflows.
**MIT-0** · Free to use, modify, and redistribute. No attribution required.⭐ 89 ·  23.3k · 336 current installs · 353 all-time installsby@Spiceman161MIT-0Security ScanVirusTotalVirusTotalBenign[View report →](https://www.virustotal.com/gui/file/2958e2fb3880e6c626c8ad134a95edfe28ea1ae64e3d829a4e6b6d1f86b2f708)OpenClawOpenClawBenignmedium confidenceThe skill's requested binaries, install method, and runtime instructions align with a Playwright MCP browser-automation tool; nothing in the package or SKILL.md is obviously inconsistent, but the npm-sourced install and lack of a homepage/author metadata leave some supply-chain uncertainty.Details ▾✓Purpose & CapabilityThe name/description (Playwright MCP browser automation) match the declared requirements: the skill lists the playwright-mcp binary and npx and provides an npm install for @playwright/mcp. The tools described (navigate, click, evaluate, screenshot, upload) are expected for a browser-automation skill.ℹInstruction ScopeSKILL.md contains concrete instructions to start the MCP server and call browser tools. It does not instruct the agent to read unrelated system files or environment variables. However, browser automation inherently has access to web content and (via browser_choose_file and output options) may interact with local files and produce extracted data — this is expected but something users should consciously restrict (allowed-hosts, blocked-origins, filesystem root restriction).ℹInstall MechanismInstall uses npm (@playwright/mcp) which is a reasonable and common distribution method for Playwright tooling. This is a moderate supply-chain risk compared with no-install skills; review of the npm package and its maintainers is advisable because the skill metadata lacks a homepage and source repository.✓CredentialsThe skill requests no environment variables, no config paths, and only needs the Playwright MCP binary and npx. Those requirements are proportional to the described functionality.✓Persistence & Privilegealways is false and the skill does not request system-wide configuration changes or permanent presence. It does not request elevated privileges in the metadata or via SKILL.md.AssessmentThis skill appears internally consistent for running Playwright MCP, but take these precautions before installing: 1) Verify the npm package: inspect its publisher, repository URL, and recent versions (npm view @playwright/mcp, review package contents or source repo). 2) Run the MCP server in a sandboxed environment (container, VM) and not as root. 3) Configure --allowed-hosts and --blocked-origins, and limit filesystem access (keep output-dir inside a controlled workspace). 4) Be aware that browser automation can access page data and local files (browser_choose_file and evaluate can be used to read and exfiltrate data); only allow trusted targets. 5) If you need high assurance, review the package source code or use an official Playwright distribution from a known repository. If you want, I can show commands to inspect the npm package metadata and contents before installing.Like a lobster shell, security has layers — review code before you run it.
Current version**v1.0.0**Download ziplatestvk972pbg6hxpha4avba5qzdx78s80ra0z
### License
MIT-0Free to use, modify, and redistribute. No attribution required.**Terms**[https://spdx.org/licenses/MIT-0.html](https://spdx.org/licenses/MIT-0.html)
### Runtime requirements
🎭 Clawdis**OS**Linux · macOS · Windows**Bins**playwright-mcp, npxFilesCompareVersions
## SKILL.md

# Playwright MCP Skill

Browser automation powered by Playwright MCP server. Control Chrome, Firefox, or WebKit programmatically.

## Installation

```bash
npm install -g @playwright/mcp
# Or
npx @playwright/mcp

```

Install browsers (first time):

```bash
npx playwright install chromium

```

## Quick Start

### Start MCP Server (STDIO mode)

```bash
npx @playwright/mcp

```

### Start with Options

```bash
# Headless mode
npx @playwright/mcp --headless

# Specific browser
npx @playwright/mcp --browser firefox

# With viewport
npx @playwright/mcp --viewport-size 1280x720

# Ignore HTTPS errors
npx @playwright/mcp --ignore-https-errors

```

## Common Use Cases

### 1. Navigate and Extract Data

```python
# MCP tools available:
# - browser_navigate: Open URL
# - browser_click: Click element
# - browser_type: Type text
# - browser_select_option: Select dropdown
# - browser_get_text: Extract text content
# - browser_evaluate: Run JavaScript
# - browser_snapshot: Get page structure
# - browser_close: Close browser

```

### 2. Form Interaction

```
1. browser_navigate to form URL
2. browser_type into input fields
3. browser_click to submit
4. browser_get_text to verify result

```

### 3. Data Extraction

```
1. browser_navigate to page
2. browser_evaluate to run extraction script
3. Parse returned JSON data

```

## MCP Tools Reference

ToolDescription`browser_navigate`Navigate to URL`browser_click`Click element by selector`browser_type`Type text into input`browser_select_option`Select dropdown option`browser_get_text`Get text content`browser_evaluate`Execute JavaScript`browser_snapshot`Get accessible page snapshot`browser_close`Close browser context`browser_choose_file`Upload file`browser_press`Press keyboard key

## Configuration Options

```bash
# Security
--allowed-hosts example.com,api.example.com
--blocked-origins malicious.com
--ignore-https-errors

# Browser settings
--browser chromium|firefox|webkit
--headless
--viewport-size 1920x1080
--user-agent "Custom Agent"

# Timeouts
--timeout-action 10000      # Action timeout (ms)
--timeout-navigation 30000  # Navigation timeout (ms)

# Output
--output-dir ./playwright-output
--save-trace
--save-video 1280x720

```

## Examples

### Login to Website

```
browser_navigate: { url: "https://example.com/login" }
browser_type: { selector: "#username", text: "user" }
browser_type: { selector: "#password", text: "pass" }
browser_click: { selector: "#submit" }
browser_get_text: { selector: ".welcome-message" }

```

### Extract Table Data

```
browser_navigate: { url: "https://example.com/data" }
browser_evaluate: { 
  script: "() => { return Array.from(document.querySelectorAll('table tr')).map(r => r.textContent); }" 
}

```

### Screenshot

```
browser_navigate: { url: "https://example.com" }
browser_evaluate: { script: "() => { document.body.style.zoom = 1; return true; }" }
# Screenshot saved via --output-dir or returned in response

```

## Security Notes

- By default restricts file system access to workspace root
- Host validation prevents navigation to untrusted domains
- Sandboxing enabled by default (use `--no-sandbox` with caution)
- Service workers blocked by default

## Troubleshooting

```bash
# Update browsers
npx playwright install chromium

# Debug mode
npx @playwright/mcp --headless=false --output-mode=stdout

# Check installation
playwright-mcp --version

```

## Links

- [Playwright Docs](https://playwright.dev)
- [MCP Protocol](https://modelcontextprotocol.io)
- [NPM Package](https://www.npmjs.com/package/@playwright/mcp)

### Files
2 totalSKILL.md4.0 KBexamples.py3.1 KBSelect a fileSelect a file to preview.
## Comments
Loading comments…