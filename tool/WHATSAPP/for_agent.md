# WHATSAPP — Agent Reference

## Quick Start
```
WHATSAPP status    # Check link state
WHATSAPP page      # Current page info
WHATSAPP chats     # List visible chats (requires link)
WHATSAPP profile   # Profile info (requires link)
```

## CDP API (`tool.WHATSAPP.logic.chrome.api`)
- `find_whatsapp_tab()` — Locate the WhatsApp Web tab
- `get_auth_state()` — Check if phone is linked (QR scanned)
- `get_page_info()` — Get page title/URL
- `get_chats()` — Read chat list from DOM (name, last message, time, unread)
- `get_profile()` — Read push name and avatar status

## Notes
- Requires Chrome CDP on port 9222
- WhatsApp Web uses QR code linking (no username/password login)
- Chats and profile require the phone to be linked first
