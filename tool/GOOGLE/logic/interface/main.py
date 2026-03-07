"""GOOGLE Tool Interface — Chrome browser automation via CDP.

Provides functions for other tools (e.g. GOOGLE.GCS) to interact with
Chrome DevTools Protocol:  session management, tab control, Colab cell
injection, Google Drive operations, and OAuth automation.

Usage from another tool::

    from tool.GOOGLE.logic.interface.main import (
        is_chrome_available,
        find_colab_tab,
        inject_and_execute,
        handle_oauth_if_needed,
    )
"""

# ---- Chrome CDP session & input ----
from tool.GOOGLE.logic.chrome.session import (  # noqa: F401
    CDP_PORT,
    CDP_TIMEOUT,
    CDPSession,
    is_chrome_cdp_available as is_chrome_available,
    is_chrome_cdp_available,
    list_tabs,
    close_tab,
    open_tab,
    real_click,
    insert_text,
    dispatch_key,
    capture_screenshot,
)

# ---- Colab integration ----
from tool.GOOGLE.logic.chrome.colab import (  # noqa: F401
    find_colab_tab,
    reopen_colab_tab,
    inject_and_execute,
)

# ---- Google Drive via CDP ----
from tool.GOOGLE.logic.chrome.drive import (  # noqa: F401
    DRIVE_MIME_TYPES,
    create_notebook,
    create_drive_file,
    delete_drive_file,
    list_drive_files,
    get_drive_about,
)

# ---- OAuth automation ----
from tool.GOOGLE.logic.chrome.oauth import (  # noqa: F401
    handle_oauth_if_needed,
    close_oauth_tabs,
    has_oauth_dialog,
    click_connect_button,
    find_oauth_tab,
)
