# LUCIDCHART — Agent Reference

## Status: PARTIALLY MIGRATED (CDMCP auth only)

DOM automation disabled. Only session/auth state checking via CDMCP remains.
Use Lucid API for all operations.

## ToS Compliance

**Risk Level: HIGH RISK**

Lucidchart ToS prohibits scraping and automated access.

### Decision Matrix

| Factor | Value |
|--------|-------|
| ToS prohibits automation | **Yes** |
| Official API exists | **Yes** (Lucid API) |
| Decision | **Use official API** |

## Migration: Lucid API

**Documentation**: https://developer.lucid.co/

### Features

- Document CRUD (Team/Enterprise only)
- Page management
- Shape and line manipulation
- Data linking
- OAuth2 authentication
- Webhooks

### Setup

1. Requires Team or Enterprise subscription
1. Register at developer.lucid.co
1. Use OAuth2 for authorization
