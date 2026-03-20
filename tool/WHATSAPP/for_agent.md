# WHATSAPP — Agent Reference

## Status: PARTIALLY MIGRATED (CDMCP auth only)

DOM automation disabled. Only QR/link authentication state checking via CDMCP remains.
All message operations must use the WhatsApp Cloud API.

## Active Commands (CDMCP auth only)

| Command | Description | Status |
|---------|-------------|--------|
| `WHATSAPP status` | Check QR link/authentication state | Active |
| `WHATSAPP page` | Show current page info | Active |

## Disabled Commands (ToS violation)

| Command | Description | Status |
|---------|-------------|--------|
| `WHATSAPP chats` | List chats | **Disabled** |
| `WHATSAPP profile` | Profile info | **Disabled** |
| `WHATSAPP search` | Search contacts | **Disabled** |
| `WHATSAPP send` | Send by phone number | **Disabled** |
| `WHATSAPP send-to` | Send by contact name | **Disabled** |

## ToS Compliance

**Status: HIGH RISK** (DOM automation disabled)

WhatsApp ToS explicitly prohibits:
> "Unofficial clients, auto-messaging, auto-dialing, or automation."

### Decision Matrix

| Factor | Value |
|--------|-------|
| ToS prohibits automation | **Yes** (explicit) |
| Official API exists | **Yes** (WhatsApp Cloud API) |
| Decision | **Use Cloud API; CDMCP for auth/login only** |

### CDMCP Retained For

- QR code scan detection (`get_auth_state()`)
- Page info checking (`get_page_info()`)

These are read-only session checks, not message automation.

## Migration: WhatsApp Cloud API

### Overview

The WhatsApp Cloud API (hosted by Meta) provides official programmatic access:
- Free tier: 1,000 service conversations/month
- 80 messages/second rate limit
- Media, templates, webhooks supported

### Setup

1. Create Meta Developer account at developers.facebook.com
2. Create a "Business" type app
3. Add WhatsApp product
4. Get permanent System User token
5. Add test recipient phone numbers

### API Endpoints

| Operation | Endpoint | Notes |
|-----------|----------|-------|
| Send text | POST `/v21.0/{phone_id}/messages` | body: `{type: "text", text: {body: "msg"}}` |
| Send template | POST `/v21.0/{phone_id}/messages` | body: `{type: "template", ...}` |
| Send media | POST `/v21.0/{phone_id}/messages` | body: `{type: "image\|document\|audio", ...}` |
| Webhooks | Configured in Meta dashboard | Receive incoming messages |

### Documentation

- https://developers.facebook.com/docs/whatsapp/cloud-api/
- https://developers.facebook.com/docs/whatsapp/getting-started/signing-up

## Return Value Format

```json
{"ok": true, "authenticated": true, "url": "...", "title": "..."}
{"ok": false, "error": "Disabled: WhatsApp ToS prohibits automated access..."}
```
