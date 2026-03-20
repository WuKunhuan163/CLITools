# YUQUE — Agent Reference

## Status: PARTIALLY MIGRATED (CDMCP auth only)

DOM automation disabled. Only session/auth state checking via CDMCP remains.
Use Yuque Developer API for all operations.

## ToS Compliance

**Risk Level: MEDIUM RISK**

Yuque provides official developer API. Premium required for new token generation.

### Decision Matrix

| Factor | Value |
|--------|-------|
| ToS restricts automation | **Yes** (implicit) |
| Official API exists | **Yes** (Yuque Developer API) |
| Decision | **Use official API** |

## Migration: Yuque Developer API

**Documentation**: https://www.yuque.com/yuque/developer

### Features

- User/group management
- Repository (知识库) CRUD
- Document CRUD with Markdown/Lake format
- Table of contents management
- Search across repos and docs
- Webhook notifications

### Setup

1. Generate token at yuque.com/settings/tokens
1. Premium subscription may be required for new tokens
1. Rate limit: 100 requests/hour (free), 5000/hour (premium)
