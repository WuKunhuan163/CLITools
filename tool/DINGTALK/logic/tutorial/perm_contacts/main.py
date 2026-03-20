"""Contacts permission tutorial for DingTalk.

Guides users through enabling contact/address-book API permissions
so they can look up users by phone, query departments, etc.
"""


def run(on_step_change=None):
    from tool.DINGTALK.logic.tutorial.common.perm_guide import run_permission_tutorial
    from tool.DINGTALK.logic.tutorial.common.prereq import validate_token

    permissions = [
        {"scope": "qyapi_get_member_by_mobile", "name": "Query user by mobile", "required": True},
        {"scope": "qyapi_get_member", "name": "Get user detail info", "required": True},
        {"scope": "Contact.User.Read", "name": "Read user contact info (new API)", "required": True},
        {"scope": "qyapi_get_dept_list", "name": "List all departments", "required": False},
        {"scope": "qyapi_get_dept_member", "name": "List department members", "required": False},
        {"scope": "qyapi_get_org_admin_list", "name": "List organization admins", "required": False},
    ]

    description = (
        "To use DINGTALK contact commands (lookup users, list departments), "
        "enable the following permissions in the DingTalk developer console.\n\n"
        "**Steps:**\n\n"
        "1. Go to https://open-dev.dingtalk.com/fe/app — select your app\n"
        "2. In the left sidebar, click **权限管理** (Permissions)\n"
        "3. Use the search box to find each permission below — it supports "
        "both formats (`Contact.User.Read` and `qyapi_get_member`) in one search\n"
        "4. Click **申请权限** (Apply) for each\n\n"
        "**Note:** Some permissions require admin approval. If your organization "
        "has approval workflows, you may need to wait for confirmation."
    )

    def test():
        result = validate_token()
        if not result.get("ok"):
            return result
        import json
        import urllib.request
        try:
            req = urllib.request.Request(
                "https://oapi.dingtalk.com/topapi/v2/user/getbymobile"
                f"?access_token={result['token']}",
                data=json.dumps({"mobile": "18876089955"}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data.get("errcode", -1) == 0:
                return {"ok": True}
            return {"ok": False, "error": data.get("errmsg", "Unknown error")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    return run_permission_tutorial(
        title="DingTalk: Contacts Permissions",
        description=description,
        permissions=permissions,
        test_func=test,
        on_step_change=on_step_change,
    )
