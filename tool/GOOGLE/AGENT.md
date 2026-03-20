# GOOGLE - Agent Guide

## Quick Reference

| Command | Purpose |
|---------|---------|
| `GOOGLE boot` | Ensure Chrome is running with CDP (auto-launches if needed). |
| `GOOGLE auth-status` | Check if a Google account is signed in via CDP. |
| `GOOGLE open-tab [url]` | Open a new Chrome tab (auto-boots Chrome if needed). |
| `GOOGLE tabs` | List currently open Chrome tabs. |
| `GOOGLE login --email <e> --password <p>` | Sign in to Google via CDP automation. |
| `GOOGLE login --email <e> --password <p> --recovery-code <c>` | Sign in with 2FA recovery code. |
| `GOOGLE logout` | Sign out of the current Google account. |
| `GOOGLE --mcp-login` | Get MCP browser login workflow (Cursor IDE browser). |

## Browser Tab Management

Boot Chrome with CDP (auto-launches if not running):
```bash
GOOGLE boot
```

Open a tab (auto-boots Chrome if needed):
```bash
GOOGLE open-tab https://example.com
GOOGLE open-tab                       # opens about:blank
```

List open tabs:
```bash
GOOGLE tabs
```

## Authentication Flow

Before using any Google CDMCP tool (GOOGLE.GC, GOOGLE.GD, GOOGLE.GDS), check login state:

```bash
GOOGLE auth-status
```

If not signed in:
1. Collect email from the user or config.
2. Collect password via `USERINPUT --enquiry --hint "Please enter your Google password"`.
3. Run: `GOOGLE login --email "user@gmail.com" --password "..." [--recovery-code "..."]`
4. Verify: `GOOGLE auth-status`

Security: Never store passwords. Collect them at runtime via USERINPUT.

## Login vs MCP-Login

- `GOOGLE login`: Uses CDP to automate the Chrome session (port 9222). For CDMCP tools.
- `GOOGLE --mcp-login`: Generates a workflow for the Cursor IDE browser. For MCP tools.

## MCP Development

When developing CDMCP tools, refer to the `cdmcp-web-exploration` skill for systematic exploration methodology including screenshot-driven development for visual multimodal agents.
