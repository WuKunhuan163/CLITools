# KLING — Agent Reference

## Status: PARTIALLY MIGRATED (CDMCP auth only)

DOM automation disabled. Only session/auth state checking via CDMCP remains.
Use Kling AI API for all operations.

## ToS Compliance

**Risk Level: MEDIUM RISK**

Official API available at klingapi.com with comprehensive SDKs.

### Decision Matrix

| Factor | Value |
|--------|-------|
| ToS restricts automation | **Yes** (implicit) |
| Official API exists | **Yes** (Kling AI API) |
| Decision | **Use official API** |

## Migration: Kling AI API

**Documentation**: https://klingapi.com/

### Features

- Image generation (text-to-image, image-to-image)
- Video generation (text-to-video, image-to-video)
- Virtual try-on
- Lip sync
- Python/Node/Java SDKs available

### Setup

1. Register at klingapi.com
1. Get API key from console
1. Install SDK: pip install kling-ai
