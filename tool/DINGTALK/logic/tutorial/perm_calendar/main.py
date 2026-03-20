"""Calendar permission tutorial for DingTalk.

Guides users through enabling Calendar/Schedule API permissions
for creating and querying DingTalk calendar events.
"""


def run(on_step_change=None):
    from tool.DINGTALK.logic.tutorial.common.perm_guide import run_permission_tutorial
    from tool.DINGTALK.logic.tutorial.common.prereq import validate_token

    permissions = [
        {"scope": "Calendar.Calendars.Read", "name": "Read calendars", "required": True},
        {"scope": "Calendar.Events.Read", "name": "Read calendar events", "required": True},
        {"scope": "Calendar.Events.Write", "name": "Create/update calendar events", "required": True},
        {"scope": "Calendar.Attendees.Read", "name": "Read event attendees", "required": False},
        {"scope": "Calendar.Attendees.Write", "name": "Manage event attendees", "required": False},
        {"scope": "Calendar.Acls.Read", "name": "Read calendar access control", "required": False},
    ]

    description = (
        "To use DingTalk calendar features (create events, query schedules), "
        "enable the following permissions in the DingTalk developer console.\n\n"
        "**Steps:**\n\n"
        "1. Go to https://open-dev.dingtalk.com/fe/app — select your app\n"
        "2. In the left sidebar, click **权限管理** (Permissions)\n"
        "3. Search for `Calendar` to find all calendar-related permissions\n"
        "4. Click **申请权限** (Apply) for the required ones\n\n"
        "**Note:** The Calendar API uses the new-style `api.dingtalk.com` endpoint.\n\n"
        "**Calendar API overview:**\n"
        "- Each user has a primary calendar and may have additional shared calendars\n"
        "- Events can have attendees, reminders, and recurrence rules\n"
        "- The `unionId` of the calendar owner is required for most operations\n\n"
        "**Related DingTalk docs:**\n"
        "  https://open.dingtalk.com/document/orgapp/calendar-overview"
    )

    def test():
        result = validate_token()
        if not result.get("ok"):
            return result
        return {"ok": True}

    return run_permission_tutorial(
        title="DingTalk: Calendar Permissions",
        description=description,
        permissions=permissions,
        test_func=test,
        on_step_change=on_step_change,
    )
