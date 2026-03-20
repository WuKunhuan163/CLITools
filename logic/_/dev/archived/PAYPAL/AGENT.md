# PAYPAL — Agent Reference

## Quick Start
```
PAYPAL status    # Check auth state
PAYPAL page      # Current page info
PAYPAL account   # Account info (requires auth)
PAYPAL activity  # Recent transactions (requires auth)
```

## CDP API (`tool.PAYPAL.logic.chrome.api`)
- `find_paypal_tab()` — Locate the PayPal browser tab
- `get_auth_state()` — Check if user is authenticated
- `get_page_info()` — Get current page title/URL/heading
- `get_account_info()` — Read name/email/balance from dashboard DOM
- `get_recent_activity()` — Read transaction rows from dashboard DOM

## Notes
- Requires Chrome CDP on port 9222
- PayPal login uses email/password (no Google sign-in)
- Account and activity commands require authenticated dashboard session

## ToS Compliance

**Status: HIGH RISK** -- PayPal explicitly prohibits "robots, spiders, scraping or other technology to access PayPal." Current implementation uses DOM scraping (9 DOM calls). **Migration needed**: PayPal REST API should be used instead. CDMCP should only be retained for initial login.

**Alternative**: PayPal REST API - account info, transactions, balance with OAuth credentials.
