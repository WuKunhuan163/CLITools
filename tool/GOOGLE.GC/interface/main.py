"""GOOGLE.GC Interface — Google Colab automation via CDP.

Provides functions for other tools to inject code into Colab notebooks,
execute cells, manage tabs, and handle OAuth flows.

Usage::

    from tool.GOOGLE.interface.main import (
        find_colab_tab,
        reopen_colab_tab,
        inject_and_execute,
    )
    from tool.GOOGLE.interface.main import (
        handle_oauth_if_needed,
        close_oauth_tabs,
    )
"""
from tool.GOOGLE.interface.main import (  # noqa: F401
    find_colab_tab,
    reopen_colab_tab,
    inject_and_execute,
)

from tool.GOOGLE.interface.main import (  # noqa: F401
    handle_oauth_if_needed,
    close_oauth_tabs,
    has_oauth_dialog,
    click_connect_button,
    find_oauth_tab,
)
