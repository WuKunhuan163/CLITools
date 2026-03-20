# GITLAB

GitLab integration via GitLab MCP

**Purpose**: Manage repositories, issues, merge requests, and CI/CD through GitLab.

## Capabilities

- repositories
- issues
- merge-requests
- pipelines

## Usage

```bash
GITLAB status          # Show tool status
GITLAB config <k> <v>  # Set configuration
GITLAB setup           # Install dependencies
```

## Environment Variables

- `GITLAB_TOKEN`
- `GITLAB_URL`

## API Key

Obtain credentials at: https://gitlab.com/-/profile/personal_access_tokens

## MCP Backend

Package: `gitlab-mcp`
