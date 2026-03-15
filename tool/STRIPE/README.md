# STRIPE

Payment processing via Stripe MCP

**Purpose**: Manage payments, customers, and subscriptions through Stripe.

## Capabilities

- create-payment
- manage-customers
- list-transactions
- refunds

## Usage

```bash
STRIPE status          # Show tool status
STRIPE config <k> <v>  # Set configuration
STRIPE setup           # Install dependencies
```

## Environment Variables

- `STRIPE_SECRET_KEY`

## API Key

Obtain credentials at: https://dashboard.stripe.com/apikeys

## MCP Backend

Package: `@stripe/mcp`
