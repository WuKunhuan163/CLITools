# STRIPE - Agent Guide

Payment processing via Stripe MCP

## Quick Reference

```bash
STRIPE status          # Check status and capabilities
STRIPE config <k> <v>  # Set API credentials
STRIPE setup           # Install dependencies and configure
```

## Capabilities

- create-payment
- manage-customers
- list-transactions
- refunds

Required credentials: `STRIPE_SECRET_KEY`

## Notes

- Run `STRIPE setup` before first use to install MCP dependencies.
- API credentials are stored in `tool/STRIPE/data/config.json`.
- Use `STRIPE --json` for machine-readable output.
