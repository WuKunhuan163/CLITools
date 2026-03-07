# PLAID - Agent Guide

Financial data integration via Plaid API

## Quick Reference

```bash
PLAID status          # Check status and capabilities
PLAID config <k> <v>  # Set API credentials
PLAID setup           # Install dependencies and configure
```

## Capabilities

- link-accounts
- transactions
- balances
- identity-verification

Required credentials: `PLAID_CLIENT_ID`, `PLAID_SECRET`

## Notes

- Run `PLAID setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/PLAID/data/config.json`.
- Use `PLAID --json` for machine-readable output.
