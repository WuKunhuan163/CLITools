# WHIMSICAL — Agent Reference

## Status: STUB (no CDMCP implementation)

No CDMCP implementation. Use Whimsical Beta API for all operations.

## ToS Compliance

**Risk Level: MEDIUM RISK**

Whimsical ToS prohibits scraping and automated access to the service.

### Decision Matrix

| Factor | Value |
|--------|-------|
| ToS restricts automation | **Yes** (implicit) |
| Official API exists | **Yes** (Whimsical Beta API) |
| Decision | **Use official API** |

## Migration: Whimsical Beta API

**Documentation**: https://whimsical.com/developers

### Features

- Workspace listing
- Board/document CRUD
- Export to image/PDF
- Embed generation

### Setup

1. Request API access (beta program)
1. Generate API key from workspace settings
