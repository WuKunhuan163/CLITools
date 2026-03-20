"""Hook interface: on_post_push

Fired after a successful ``git push`` operation.
Implementations receive the project root, branch, and remote name.
"""
from interface.hooks import HookInterface


class OnPostPush(HookInterface):
    event_name = "on_post_push"
    description = "Fired after a successful git push."
