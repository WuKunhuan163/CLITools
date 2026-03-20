# DINGTALK — Agent Reference

## Status: ACTIVE (Official API)

Uses DingTalk Open Platform REST API. No browser automation. Fully ToS compliant.

## Quick Start

```bash
DINGTALK status                                    # Check config
DINGTALK config app_key <KEY>                      # Set credentials
DINGTALK config app_secret <SECRET>
DINGTALK config agent_id <ID>                      # For work notifications
DINGTALK config operator_id <USERID>               # For todo creation

DINGTALK contact --phone +8613925243201            # Look up user by phone
DINGTALK contact "张三"                             # Search by name
DINGTALK send "Hello" --phone +8618876089955       # Send by phone number
DINGTALK send "Hello" --userid user123             # Send by userId
DINGTALK webhook "部署完成"                         # Send via webhook
DINGTALK notify "请审批" --userid user123           # Work notification
DINGTALK todo "完成竞品分析"                        # Create todo
```

## Architecture

### API Client (`logic/api.py`)

Core module implementing DingTalk Open Platform API:

| Function | Description |
|----------|-------------|
| `get_user_by_mobile(phone)` | Phone -> userId lookup |
| `get_user_detail(userid)` | Full user profile |
| `search_users(query)` | Search by name/keyword |
| `send_robot_message(user_ids, content)` | Robot 1:1 message |
| `send_robot_group_message(conv_id, content)` | Robot group message |
| `send_webhook_message(url, content)` | Webhook robot message |
| `send_work_notification(user_ids, content)` | Work notification |
| `create_todo(subject)` | Create todo task |
| `send_message_to_phone(phone, content)` | Convenience: phone -> send |

### Token Management

Two token types, both cached with expiry:

| Type | Endpoint | Usage | Cache Key |
|------|----------|-------|-----------|
| New token | `POST api.dingtalk.com/v1.0/oauth2/accessToken` | Header: `x-acs-dingtalk-access-token` | `new_token` |
| Old token | `GET oapi.dingtalk.com/gettoken` | Query: `?access_token=` | `old_token` |

### Identity System

DingTalk uses `userId` (= `staffId`) for all messaging APIs:

| ID Type | Scope | Use for Messaging |
|---------|-------|-------------------|
| `userId` | Single enterprise | Yes (required) |
| `unionId` | Cross-enterprise | No (convert first) |

Phone number -> userId: `POST /topapi/v2/user/getbymobile`

### Config (`data/config.json`)

| Key | Required For | Description |
|-----|-------------|-------------|
| `app_key` | All | DingTalk app key (= robotCode) |
| `app_secret` | All | DingTalk app secret |
| `agent_id` | Work notifications | App agent ID |
| `operator_id` | Todo creation | Operator's userId |
| `webhook_url` | Webhook messages | Group webhook URL |
| `webhook_secret` | Webhook (signed) | HMAC signing secret |

## ToS Compliance

**Status: COMPLIANT** (official API)

Uses only the DingTalk Open Platform REST API. No browser automation,
scraping, or reverse engineering. All operations go through official
API endpoints with proper authentication.

### Source Attribution

API implementation based on:
- [DingTalk Open Platform](https://open.dingtalk.com/)
- [dingtalk-skills](https://github.com/breath57/dingtalk-skills) (MIT, API reference patterns)
- [DingTalk Stream SDK](https://github.com/open-dingtalk/dingtalk-stream-sdk-python)

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `401` | Token expired | Auto-refreshes |
| `403` | Permission denied | Enable API permissions in DingTalk admin |
| `60121` | User not found | Check userId/phone |
| `88` | Invalid agent_id | Verify in app settings |
| `310000` | Webhook sign mismatch | Check timestamp/secret |
