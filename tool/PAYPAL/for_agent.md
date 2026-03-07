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
