# MIRO — Agent Reference

## Status: STUB (no CDMCP implementation)

No CDMCP implementation. Use Miro REST API v2 for all operations.

## ToS Compliance

**Risk Level: LOW RISK**

Miro provides comprehensive official REST API. No need for browser automation.

### Decision Matrix

| Factor | Value |
|--------|-------|
| ToS restricts automation | **Silent** |
| Official API exists | **Yes** (Miro REST API v2) |
| Decision | **Use official API** |

## Migration: Miro REST API v2

**Documentation**: https://developers.miro.com/

### Features

- Board CRUD and sharing
- Item management (sticky notes, shapes, text, connectors)
- Frame management
- Tags and comments
- Webhooks for real-time events
- OAuth2 authentication
- SDKs: JavaScript, Python, Ruby

### Setup

1. Create app at miro.com/app/settings/user-profile/apps
1. Use OAuth2 or token-based auth
1. Rate limit: 100 credits/min per app
