# FIGMA — Agent Reference

## Status: PARTIALLY MIGRATED (CDMCP auth only)

DOM automation disabled. Only session/auth state checking via CDMCP remains.
Use Figma REST API + Plugin API for all operations.

## ToS Compliance

**Risk Level: HIGH RISK**

Figma ToS prohibits scraping, automated access, and reverse engineering.

### Decision Matrix

| Factor | Value |
|--------|-------|
| ToS prohibits automation | **Yes** |
| Official API exists | **Yes** (Figma REST API + Plugin API) |
| Decision | **Use official API** |

## Migration: Figma REST API + Plugin API

**Documentation**: https://www.figma.com/developers/api

### Features

- File/node access and export (GET /v1/files/:key)
- Comments API (GET/POST /v1/files/:key/comments)
- Team/project listing
- Images export (GET /v1/images/:key)
- Component/style library access
- Webhooks for file changes
- OAuth2 authentication

### Setup

1. Create app at figma.com/developers
1. Use OAuth2 or Personal Access Token
1. Rate limit: ~30 requests/minute
