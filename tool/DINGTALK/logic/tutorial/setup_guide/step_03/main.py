"""Step 3: Add API Permissions."""
from pathlib import Path
from interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)

def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)


def build_step(frame, win):
    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _(
        "tutorial_step3_title",
        "Step 3: Add API Permissions"
    ), is_title=True)

    content_block = win.add_block(frame)
    content = _(
        "tutorial_step3_content",
        "Your app needs API permissions to function. Go to your app's settings "
        "in the [Developer Console](https://open-dev.dingtalk.com/fe/app) and "
        "enable the required scopes.\n\n"
        "**How to add permissions:**\n\n"
        "1. Open your app in the Developer Console\n"
        "2. Go to **Permission Management** (权限管理) in the sidebar\n"
        "3. Use the search box — it supports both `Contact.User.Read` style "
        "and `qyapi_get_member` style names in one search\n"
        "4. Click **申请权限** (Apply) for each permission\n\n"
        "**Required Permissions:**\n\n"
        "- `qyapi_get_member_by_mobile` — Look up users by phone number\n"
        "- `qyapi_get_member` — Get user details\n"
        "- `Contact.User.Read` — Read contact information\n\n"
        "**Recommended (for full features):**\n\n"
        "- `qyapi_message_corpconversation_asyncsend_v2` — Send work notifications\n"
        "- `qyapi_robot_sendmsg` — Send robot 1:1 messages\n"
        "- `Todo.Todo.Write` — Create and manage todo tasks\n\n"
        "Reference: [API Permission Documentation](https://open.dingtalk.com/document/orgapp/add-api-permission)\n\n"
        "After enabling permissions, click **Next** to validate your credentials."
    )
    win.add_inline_links(content_block, content)
