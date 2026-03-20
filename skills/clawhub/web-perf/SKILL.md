---
name: web-perf
title: "Web Perf"
description: "Analyzes web performance using Chrome DevTools MCP. Measures Core Web Vitals (FCP, LCP, TBT, CLS, Speed Index), identifies render-blocking resources, network dependency chains, layout shifts, caching…"
source: clawhub
url: https://clawhub.ai/skills/web-perf
imported: 2026-03-17
---

**Skill flagged — suspicious patterns detected**ClawHub Security flagged this skill as suspicious. Review the scan results before using.

# Web Perf
Analyzes web performance using Chrome DevTools MCP. Measures Core Web Vitals (FCP, LCP, TBT, CLS, Speed Index), identifies render-blocking resources, network dependency chains, layout shifts, caching issues, and accessibility gaps. Use when asked to audit, profile, debug, or optimize page load performance, Lighthouse scores, or site speed.
**MIT-0** · Free to use, modify, and redistribute. No attribution required.⭐ 2 ·  4k · 20 current installs · 20 all-time installsby@elithrarMIT-0Security ScanVirusTotalVirusTotalSuspicious[View report →](https://www.virustotal.com/gui/file/4ec32bae58cb670371fae795600d232240206ea7b0141cfdc9a953c18563c73d)OpenClawOpenClawBenignmedium confidenceThe skill's instructions and requirements are internally consistent with a web-performance audit using Chrome DevTools MCP; no unrelated secrets or installs are demanded, but it omits explicit mentions of platform dependencies and instructs users to fetch/run a third‑party npm package via npx.Details ▾✓Purpose & CapabilityThe name/description (web performance audit, Core Web Vitals, network and a11y checks) matches the SKILL.md workflow and the MCP tool calls (navigate_page, performance_start_trace, performance_analyze_insight, list_network_requests, take_snapshot). The actions requested are appropriate for the stated purpose.ℹInstruction ScopeThe instructions stay focused on auditing and (optionally) inspecting a codebase. They explicitly tell the agent to query the MCP server and to scan the local repo for build/config files when codebase access is available — this is appropriate for a code audit but does involve reading project files (expected). No instructions request unrelated system secrets or external exfiltration.ℹInstall MechanismThere is no formal install spec, but the SKILL.md recommends adding an MCP config that runs `npx -y chrome-devtools-mcp@latest`. That implicitly requires node/npx and will fetch/run code from the public npm registry. This is a reasonable runtime step for MCP usage but is not declared in the skill metadata and carries the usual risk of running third‑party npm packages.ℹCredentialsThe skill declares no required environment variables or credentials (appropriate). However, it implicitly requires local platform dependencies (node/npx, a Chrome/Chromium accessible to MCP) which are not listed. No sensitive credentials are requested.✓Persistence & PrivilegeThe skill is instruction-only, has no install spec that writes files, and does not request 'always: true' or other elevated/persistent privileges. It does not ask to modify other skills or global agent settings.Scan Findings in Context[no_regex_findings] expected: This skill contains no code files (instruction-only), so the regex-based scanner had nothing to analyze — that is expected for an instruction-only MCP workflow.AssessmentThis skill is coherent for auditing site performance, but review a few practical points before installing: 1) The SKILL.md asks you to run an MCP helper via `npx chrome-devtools-mcp@latest`; that will download and execute code from npm — inspect that package/source first and only run it in an environment you trust. 2) The instructions implicitly require node/npx and a Chrome/Chromium reachable by the MCP server; ensure those are installed and isolated from sensitive data. 3) If you plan to use Phase 5 (codebase analysis), the agent will access your repository files — only allow that on repos you control or where you’re comfortable sharing code. 4) No secrets or environment variables are requested by the skill, which is good. If you want higher assurance, ask the publisher for the MCP helper’s repository and a signed release, or run the MCP helper in an isolated container/VM before using this skill.Like a lobster shell, security has layers — review code before you run it.
Current version**v1.0.0**Download ziplatestvk972g5teq9x1pnfhynry0wh1e17yq3ek
### License
MIT-0Free to use, modify, and redistribute. No attribution required.**Terms**[https://spdx.org/licenses/MIT-0.html](https://spdx.org/licenses/MIT-0.html)FilesCompareVersions
## SKILL.md

# Web Performance Audit

Audit web page performance using Chrome DevTools MCP tools. This skill focuses on Core Web Vitals, network optimization, and high-level accessibility gaps.

## FIRST: Verify MCP Tools Available

**Run this before starting.** Try calling `navigate_page` or `performance_start_trace`. If unavailable, STOP—the chrome-devtools MCP server isn't configured.

Ask the user to add this to their MCP config:

```json
"chrome-devtools": {
  "type": "local",
  "command": ["npx", "-y", "chrome-devtools-mcp@latest"]
}

```

## Key Guidelines

- **Be assertive**: Verify claims by checking network requests, DOM, or codebase—then state findings definitively.
- **Verify before recommending**: Confirm something is unused before suggesting removal.
- **Quantify impact**: Use estimated savings from insights. Don't prioritize changes with 0ms impact.
- **Skip non-issues**: If render-blocking resources have 0ms estimated impact, note but don't recommend action.
- **Be specific**: Say "compress hero.png (450KB) to WebP" not "optimize images".
- **Prioritize ruthlessly**: A site with 200ms LCP and 0 CLS is already excellent—say so.

## Quick Reference

TaskTool CallLoad page`navigate_page(url: "...")`Start trace`performance_start_trace(autoStop: true, reload: true)`Analyze insight`performance_analyze_insight(insightSetId: "...", insightName: "...")`List requests`list_network_requests(resourceTypes: ["Script", "Stylesheet", ...])`Request details`get_network_request(reqid: <id>)`A11y snapshot`take_snapshot(verbose: true)`

## Workflow

Copy this checklist to track progress:

```
Audit Progress:
- [ ] Phase 1: Performance trace (navigate + record)
- [ ] Phase 2: Core Web Vitals analysis (includes CLS culprits)
- [ ] Phase 3: Network analysis
- [ ] Phase 4: Accessibility snapshot
- [ ] Phase 5: Codebase analysis (skip if third-party site)

```

### Phase 1: Performance Trace

- 
Navigate to the target URL:

```
navigate_page(url: "<target-url>")

```

- 
Start a performance trace with reload to capture cold-load metrics:

```
performance_start_trace(autoStop: true, reload: true)

```

- 
Wait for trace completion, then retrieve results.

**Troubleshooting:**

- If trace returns empty or fails, verify the page loaded correctly with `navigate_page` first
- If insight names don't match, inspect the trace response to list available insights

### Phase 2: Core Web Vitals Analysis

Use `performance_analyze_insight` to extract key metrics.

**Note:** Insight names may vary across Chrome DevTools versions. If an insight name doesn't work, check the `insightSetId` from the trace response to discover available insights.

Common insight names:

MetricInsight NameWhat to Look ForLCP`LCPBreakdown`Time to largest contentful paint; breakdown of TTFB, resource load, render delayCLS`CLSCulprits`Elements causing layout shifts (images without dimensions, injected content, font swaps)Render Blocking`RenderBlocking`CSS/JS blocking first paintDocument Latency`DocumentLatency`Server response time issuesNetwork Dependencies`NetworkRequestsDepGraph`Request chains delaying critical resources
Example:

```
performance_analyze_insight(insightSetId: "<id-from-trace>", insightName: "LCPBreakdown")

```

**Key thresholds (good/needs-improvement/poor):**

- TTFB: < 800ms / < 1.8s / > 1.8s
- FCP: < 1.8s / < 3s / > 3s
- LCP: < 2.5s / < 4s / > 4s
- INP: < 200ms / < 500ms / > 500ms
- TBT: < 200ms / < 600ms / > 600ms
- CLS: < 0.1 / < 0.25 / > 0.25
- Speed Index: < 3.4s / < 5.8s / > 5.8s

### Phase 3: Network Analysis

List all network requests to identify optimization opportunities:

```
list_network_requests(resourceTypes: ["Script", "Stylesheet", "Document", "Font", "Image"])

```

**Look for:**

- **Render-blocking resources**: JS/CSS in `<head>` without `async`/`defer`/`media` attributes
- **Network chains**: Resources discovered late because they depend on other resources loading first (e.g., CSS imports, JS-loaded fonts)
- **Missing preloads**: Critical resources (fonts, hero images, key scripts) not preloaded
- **Caching issues**: Missing or weak `Cache-Control`, `ETag`, or `Last-Modified` headers
- **Large payloads**: Uncompressed or oversized JS/CSS bundles
- **Unused preconnects**: If flagged, verify by checking if ANY requests went to that origin. If zero requests, it's definitively unused—recommend removal. If requests exist but loaded late, the preconnect may still be valuable.

For detailed request info:

```
get_network_request(reqid: <id>)

```

### Phase 4: Accessibility Snapshot

Take an accessibility tree snapshot:

```
take_snapshot(verbose: true)

```

**Flag high-level gaps:**

- Missing or duplicate ARIA IDs
- Elements with poor contrast ratios (check against WCAG AA: 4.5:1 for normal text, 3:1 for large text)
- Focus traps or missing focus indicators
- Interactive elements without accessible names

## Phase 5: Codebase Analysis

**Skip if auditing a third-party site without codebase access.**

Analyze the codebase to understand where improvements can be made.

### Detect Framework & Bundler

Search for configuration files to identify the stack:

ToolConfig FilesWebpack`webpack.config.js`, `webpack.*.js`Vite`vite.config.js`, `vite.config.ts`Rollup`rollup.config.js`, `rollup.config.mjs`esbuild`esbuild.config.js`, build scripts with `esbuild`Parcel`.parcelrc`, `package.json` (parcel field)Next.js`next.config.js`, `next.config.mjs`Nuxt`nuxt.config.js`, `nuxt.config.ts`SvelteKit`svelte.config.js`Astro`astro.config.mjs`
Also check `package.json` for framework dependencies and build scripts.

### Tree-Shaking & Dead Code

- **Webpack**: Check for `mode: 'production'`, `sideEffects` in package.json, `usedExports` optimization
- **Vite/Rollup**: Tree-shaking enabled by default; check for `treeshake` options
- **Look for**: Barrel files (`index.js` re-exports), large utility libraries imported wholesale (lodash, moment)

### Unused JS/CSS

- Check for CSS-in-JS vs. static CSS extraction
- Look for PurgeCSS/UnCSS configuration (Tailwind's `content` config)
- Identify dynamic imports vs. eager loading

### Polyfills

- Check for `@babel/preset-env` targets and `useBuiltIns` setting
- Look for `core-js` imports (often oversized)
- Check `browserslist` config for overly broad targeting

### Compression & Minification

- Check for `terser`, `esbuild`, or `swc` minification
- Look for gzip/brotli compression in build output or server config
- Check for source maps in production builds (should be external or disabled)

## Output Format

Present findings as:

- **Core Web Vitals Summary** - Table with metric, value, and rating (good/needs-improvement/poor)
- **Top Issues** - Prioritized list of problems with estimated impact (high/medium/low)
- **Recommendations** - Specific, actionable fixes with code snippets or config changes
- **Codebase Findings** - Framework/bundler detected, optimization opportunities (omit if no codebase access)

### Files
1 totalSKILL.md7.4 KBSelect a fileSelect a file to preview.
## Comments
Loading comments…