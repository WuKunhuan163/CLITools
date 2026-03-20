# WHATSAPP — Agent Reference

## Quick Start
```
WHATSAPP status                      # Check link state
WHATSAPP chats                       # List visible chats
WHATSAPP search "John"               # Search contacts/chats by name
WHATSAPP send +85290549853 "Hello"   # Send message by phone number
WHATSAPP send-to "John Doe" "Hello"  # Send message by contact name
WHATSAPP profile                     # Profile info
```

## CDP API (`tool.WHATSAPP.logic.chrome.api`)
- `get_auth_state()` — Check if phone is linked (QR scanned)
- `get_chats()` — Read chat list from DOM (name, last message, time, unread count)
- `search_contact(query)` — Search contacts/chats, returns matching names
- `send_message(phone, message)` — Send to phone number via wa.me deep link
- `send_to_contact(name, message)` — Send by contact name (searches, opens chat, sends)
- `get_profile()` — Read push name and avatar status
- `get_page_info()` — Get page title/URL

## Workflow: Send to All Contacts
1. `WHATSAPP chats` — get list of contact names
2. For each name: `WHATSAPP send-to "<name>" "<message>"`

## Notes
- Requires Chrome CDP on port 9222
- WhatsApp Web uses QR code linking (no username/password login)
- `send_to_contact` uses search UI to find contacts — works with partial name matches
- `send_message` requires phone number digits (strips non-digits automatically)

## ToS Compliance

**Status: HIGH RISK** -- WhatsApp explicitly prohibits "unofficial clients, auto-messaging, auto-dialing, or automation." Current implementation uses DOM scraping (52 DOM calls) which violates WhatsApp ToS. **Migration needed**: WhatsApp Cloud API or WhatsApp Business API should be used instead. CDMCP should only be retained for initial login/authentication. Account ban risk is HIGH if automation is detected.

**Alternative**: WhatsApp Cloud API (requires Meta Business account) - supports sending/receiving messages, media, templates.
