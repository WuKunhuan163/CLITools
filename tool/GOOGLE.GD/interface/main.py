"""GOOGLE.GD Interface — Google Drive file operations via CDP.

Provides functions for other tools to perform Drive CRUD operations
using the authenticated gapi.client session in a Colab tab.

Usage::

    from tool.GOOGLE.logic.chrome.drive import (
        list_drive_files,
        create_drive_file,
        delete_drive_file,
        create_notebook,
        get_drive_about,
        DRIVE_MIME_TYPES,
    )
"""
from tool.GOOGLE.logic.chrome.drive import (  # noqa: F401
    DRIVE_MIME_TYPES,
    create_notebook,
    create_drive_file,
    delete_drive_file,
    list_drive_files,
    get_drive_about,
)
