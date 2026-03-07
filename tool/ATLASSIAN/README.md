# ATLASSIAN

Jira and Confluence integration via Atlassian MCP

**Purpose**: Manage Jira issues, Confluence pages, and Compass components.

## Capabilities

- jira-issues
- confluence-pages
- search
- create-update

## Usage

```bash
ATLASSIAN status          # Show tool status
ATLASSIAN config <k> <v>  # Set configuration
ATLASSIAN setup           # Install dependencies
```

## Environment Variables

- `ATLASSIAN_API_TOKEN`
- `ATLASSIAN_EMAIL`
- `ATLASSIAN_SITE_URL`

## API Key

Obtain credentials at: https://id.atlassian.com/manage-profile/security/api-tokens

## MCP Backend

Package: `atlassian-mcp-server`
