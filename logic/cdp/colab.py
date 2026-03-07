"""Backward-compatibility shim — re-exports from tool.GOOGLE.logic.chrome.

All Chrome CDP functionality has been refactored into the GOOGLE tool.
This module uses the universal path resolver, then re-exports the public
API so that ``from logic.cdp.colab import ...`` continues to work.
"""
from logic.resolve import setup_paths as _setup_paths
_setup_paths(__file__)

from tool.GOOGLE.logic.chrome.session import (  # noqa: F401
    CDP_PORT,
    CDP_TIMEOUT,
    CDPSession,
    is_chrome_cdp_available,
)
from tool.GOOGLE.logic.chrome.colab import (  # noqa: F401
    find_colab_tab,
    reopen_colab_tab as _reopen_colab_tab,
    inject_and_execute,
)
from tool.GOOGLE.logic.chrome.drive import (  # noqa: F401
    DRIVE_MIME_TYPES,
    create_notebook,
    create_drive_file,
    delete_drive_file,
    list_drive_files,
    get_drive_about,
)
