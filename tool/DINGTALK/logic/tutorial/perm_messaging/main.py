"""Messaging permission tutorial for DingTalk.

Guides users through enabling message-related API permissions
for robot messages, work notifications, and group chat.
"""


def run(on_step_change=None):
    from tool.DINGTALK.logic.tutorial.common.perm_guide import run_permission_tutorial
    from tool.DINGTALK.logic.tutorial.common.prereq import validate_token

    permissions = [
        {"scope": "qyapi_chat_manage", "name": "Manage group chats (create, update)", "required": False},
        {"scope": "qyapi_chat_send", "name": "Send messages to group chats", "required": True},
        {"scope": "qyapi_robot_sendmsg", "name": "Send robot messages to users", "required": True},
        {"scope": "cspace_oa_top_worknotification", "name": "Send work notifications", "required": True},
        {"scope": "Message.Send", "name": "Send messages (new API)", "required": False},
        {"scope": "Robot.Message.Send", "name": "Send robot messages (new API)", "required": False},
    ]

    description = (
        "To use DINGTALK messaging commands (send, notify, webhook), "
        "enable the following permissions in the DingTalk developer console.\n\n"
        "**Steps:**\n\n"
        "1. Go to https://open-dev.dingtalk.com/fe/app — select your app\n"
        "2. In the left sidebar, click **权限管理** (Permissions)\n"
        "3. Search for each permission scope below\n"
        "4. Click **申请权限** (Apply) for each one\n\n"
        "**Robot messages** (qyapi_robot_sendmsg) allow your app to send "
        "direct messages to individual users via the app's robot identity.\n\n"
        "**Work notifications** (cspace_oa_top_worknotification) appear in "
        "the user's DingTalk work notification stream — suitable for announcements.\n\n"
        "**Group chat** permissions (qyapi_chat_*) allow creating and sending "
        "messages to DingTalk group conversations.\n\n"
        "**Optional: Custom Webhook**\n"
        "For webhook-based messaging, you can also create a custom robot in "
        "any group chat. This requires no API permission — just the webhook URL "
        "and optional signing secret."
    )

    def test():
        result = validate_token()
        if not result.get("ok"):
            return result
        return {"ok": True}

    return run_permission_tutorial(
        title="DingTalk: Messaging Permissions",
        description=description,
        permissions=permissions,
        test_func=test,
        on_step_change=on_step_change,
    )
