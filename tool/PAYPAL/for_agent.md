# PAYPAL - Agent Guide

PayPal payment integration

## Quick Reference

```bash
PAYPAL status          # Check status and capabilities
PAYPAL config <k> <v>  # Set API credentials
PAYPAL setup           # Install dependencies and configure
```

## Capabilities

- create-payment
- capture-payment
- list-transactions
- refunds

Required credentials: `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`

## Notes

- Run `PAYPAL setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/PAYPAL/data/config.json`.
- Use `PAYPAL --json` for machine-readable output.
