---
name: cdmcp-web-exploration
description: Systematic approach to exploring and automating web application interactions via CDMCP. Use when developing new MCP tool integrations, exploring web app DOM structures, or creating Turing machine workflows for browser automation.
---

# CDMCP Web Exploration

## When to Use

Use this skill when:
- Building a new CDMCP tool for a web service
- Exploring a web app's DOM to find interaction targets
- Creating automated workflows for browser-based operations

## CRITICAL: Terms of Service Compliance Check

**Before developing any CDMCP-based tool, you MUST:**

1. **Find the service's Terms of Service / Terms of Use** (search for `<service> terms of service` or look for links in the footer/settings).
2. **Check if UI automation is prohibited.** Look for clauses about:
   - "Automated access", "bots", "scrapers", "robots"
   - "Non-API access", "unauthorized automated means"
   - "Reverse engineering", "interfering with the service"
   - "Accessing the service through unauthorized means"
3. **Search for an official API.** Many services offer REST APIs, GraphQL endpoints, or OAuth-based integrations that are explicitly permitted.
4. **Decision matrix:**

| Scenario | Action |
|---|---|
| ToS explicitly prohibits UI automation AND official API exists | Use the official API instead |
| ToS explicitly prohibits UI automation, no API | Do NOT build the tool; document the limitation |
| ToS is silent on automation AND official API exists | Prefer the API; use CDMCP only for auth/bootstrap |
| ToS is silent on automation, no API | CDMCP acceptable with caution |
| ToS explicitly allows automation | CDMCP acceptable |

5. **Document your finding** in the tool's `AGENT.md` under a `## ToS Compliance` section.
6. **CDMCP for login/auth is generally acceptable** -- the concern is about automating post-login interactions (data scraping, button clicking, form filling) at scale.

**Example of a compliant approach (ShowDoc):** Use CDMCP only for session management (opening tab, auth detection), but call the service's REST API via in-page `fetch()` for all data operations.

## Exploration Process

### 1. Start a Session

```bash
CDMCP --mcp-session start --name "explore_service"
```

### 2. Navigate to the Target Page

```bash
CDMCP --mcp-navigate --url "https://app.example.com/dashboard"
```

### 3. Capture the DOM Structure

```bash
CDMCP --mcp-screenshot --path "/tmp/explore_01.png"
```

### 4. Query DOM Elements

Use CDP `Runtime.evaluate` to explore the page:

```python
cdp.evaluate('document.querySelectorAll("button").length')
cdp.evaluate('document.querySelector("nav").innerText')
cdp.evaluate('JSON.stringify(Array.from(document.querySelectorAll("[data-testid]")).map(el => ({tag: el.tagName, id: el.dataset.testid})))')
```

### 5. Identify Stable Selectors

Prefer in this order:
1. `data-testid` or `data-cy` attributes
2. `aria-label` attributes
3. Unique `id` attributes
4. Semantic CSS selectors (`.sidebar-nav > .item:nth-child(2)`)
5. XPath (last resort)

### 6. Test Interactions

```python
cdp.evaluate('document.querySelector("[data-testid=submit-btn]").click()')
```

### 7. Document Findings

Create a `AGENT.md` in the tool directory documenting:
- Page structure and navigation flow
- Key selectors for each operation
- Authentication requirements
- Rate limits or timing constraints

## Guidelines

1. Always screenshot before and after interactions
2. Wait for page loads (`document.readyState === "complete"`)
3. Handle dynamic content (SPAs) with polling or mutation observers
4. Test with different viewport sizes
5. Document fragile selectors that may break on UI updates
