# WPS — Agent Reference

## Status: PARTIALLY MIGRATED (CDMCP auth only)

DOM automation disabled. Only session/auth state checking via CDMCP remains.
Use KDocs Developer Platform API for all operations.

## ToS Compliance

**Risk Level: MEDIUM RISK**

WPS ToS restricts automated access. KDocs Developer Platform provides official API.

### Decision Matrix

| Factor | Value |
|--------|-------|
| ToS restricts automation | **Yes** (implicit) |
| Official API exists | **Yes** (KDocs Developer Platform API) |
| Decision | **Use official API** |

## Migration: KDocs Developer Platform API

**Documentation**: https://open.wps.cn/

### Features

- Document CRUD (create, read, update, delete)
- Spreadsheet operations
- Presentation management
- File sharing and permissions
- Webhook notifications

### Setup

1. Register at open.wps.cn
1. Create application
1. Use OAuth2 for user authorization
