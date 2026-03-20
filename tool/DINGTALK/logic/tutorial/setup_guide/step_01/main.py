"""Step 1: Create a DingTalk Organization & Internal App."""
from pathlib import Path
from interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)

def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)


def build_step(frame, win):
    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _(
        "tutorial_step1_title",
        "Step 1: Create Organization & App"
    ), is_title=True)

    content_block = win.add_block(frame)
    content = _(
        "tutorial_step1_content",
        "**Prerequisites:**\n\n"
        "1. You need a DingTalk organization. If you don't have one, "
        "create it in the DingTalk mobile or desktop app first.\n\n"
        "**Create an Internal App:**\n\n"
        "2. Open the [DingTalk Developer Platform](https://open-dev.dingtalk.com/) "
        "and log in with your DingTalk account.\n\n"
        "3. Navigate to [App Development](https://open-dev.dingtalk.com/fe/app) "
        "and click **Create App** (创建应用).\n\n"
        "4. Choose **Enterprise Internal App** (企业内部应用) and give it a name "
        "(e.g., 'AITerminalTools').\n\n"
        "5. Enable the [APIs](https://open.dingtalk.com/developer/list/) "
        "you need for your integration.\n\n"
        "Once your app is created, click **Next** to get your credentials."
    )
    win.add_inline_links(content_block, content)
