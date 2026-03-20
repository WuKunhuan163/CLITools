# GOOGLE.GD — Agent Reference

## Status: STUB (no implementation)

No CDMCP implementation. Use Google Drive API v3 for all operations.

## ToS Compliance

**Risk Level: LOW RISK**

Google Drive has comprehensive official API. Use it instead of browser automation.

### Decision Matrix

| Factor | Value |
|--------|-------|
| ToS restricts automation | **Silent** |
| Official API exists | **Yes** (Google Drive API v3) |
| Decision | **Use official API** |

## Migration: Google Drive API v3

**Documentation**: https://developers.google.com/drive/api/v3

### Features

- File CRUD (upload, download, copy, move, delete)
- Folder management
- Sharing and permissions
- Search with query language
- Export to multiple formats
- Revision history
- Real-time change notifications (webhooks)

### Setup

1. Enable Drive API in Google Cloud Console
1. Create OAuth2 credentials or service account
1. pip install google-api-python-client google-auth
