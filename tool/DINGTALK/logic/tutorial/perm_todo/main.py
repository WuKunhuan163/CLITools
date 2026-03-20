"""Todo permission tutorial for DingTalk.

Guides users through enabling Todo/task API permissions
for creating, updating, and querying DingTalk todos.
"""


def run(on_step_change=None):
    from tool.DINGTALK.logic.tutorial.common.perm_guide import run_permission_tutorial
    from tool.DINGTALK.logic.tutorial.common.prereq import validate_token

    permissions = [
        {"scope": "Todo.Todo.Create", "name": "Create todo items", "required": True},
        {"scope": "Todo.Todo.Read", "name": "Read todo items", "required": True},
        {"scope": "Todo.Todo.Write", "name": "Update/delete todo items", "required": True},
        {"scope": "Todo.Category.Read", "name": "Read todo categories", "required": False},
        {"scope": "Todo.Category.Write", "name": "Manage todo categories", "required": False},
    ]

    description = (
        "To use DINGTALK todo commands (create tasks, assign to users), "
        "enable the following permissions in the DingTalk developer console.\n\n"
        "**Steps:**\n\n"
        "1. Go to https://open-dev.dingtalk.com/fe/app — select your app\n"
        "2. In the left sidebar, click **权限管理** (Permissions)\n"
        "3. Search for `Todo` to find all todo-related permissions\n"
        "4. Click **申请权限** (Apply) for the required ones\n\n"
        "**Note:** Todo API uses the new-style `api.dingtalk.com` endpoint. "
        "You need both the `operator_id` (your DingTalk userId) and the target "
        "user's unionId to create todo items assigned to them.\n\n"
        "**Getting your userId:**\n"
        "Use `DINGTALK contact <your_phone>` to look up your DingTalk userId, "
        "which is needed as `operator_id` when creating todos.\n\n"
        "**Usage example:**\n"
        "  `DINGTALK todo --subject 'Review PR' --operator <your_userid>`"
    )

    def test():
        result = validate_token()
        if not result.get("ok"):
            return result
        return {"ok": True}

    return run_permission_tutorial(
        title="DingTalk: Todo Permissions",
        description=description,
        permissions=permissions,
        test_func=test,
        on_step_change=on_step_change,
    )
