# DINGTALK

DingTalk messaging and workspace integration via official Open Platform API.

## Setup

1. Create an enterprise internal application at [open.dingtalk.com](https://open.dingtalk.com/)
2. Enable required permissions: `Robot.Message.Send`, `Robot.GroupMessage.Send`, `Contact.User.Read`
3. Configure credentials:

```bash
DINGTALK config app_key <your_app_key>
DINGTALK config app_secret <your_app_secret>
DINGTALK config agent_id <your_agent_id>        # optional, for work notifications
DINGTALK config operator_id <your_user_id>      # optional, for todo creation
```

## Usage

```bash
# Check status
DINGTALK status

# Look up a contact
DINGTALK contact --phone +8613925243201
DINGTALK contact "name"

# Send message by phone number
DINGTALK send "Hello from DINGTALK" --phone +8618876089955

# Send message by userId
DINGTALK send "Hello" --userid 12345678

# Send via webhook
DINGTALK webhook "Deployment complete"

# Send work notification
DINGTALK notify "Please review" --userid 12345678

# Create todo
DINGTALK todo "Complete analysis report"
```

## API

Uses DingTalk Open Platform REST API:
- `api.dingtalk.com` (new API, v1.0)
- `oapi.dingtalk.com` (legacy API)

No browser automation. No external MCP packages required.
