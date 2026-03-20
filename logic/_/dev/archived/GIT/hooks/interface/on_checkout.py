"""Hook interface: on_checkout

Fired when switching branches via ``TOOL --dev enter`` or ``git checkout``.
Implementations receive the source branch, target branch, and project root.
"""


def on_checkout(source_branch: str, target_branch: str, project_root: str):
    """Called after a branch checkout.

    Parameters
    ----------
    source_branch : str
        Branch being left.
    target_branch : str
        Branch being entered.
    project_root : str
        Absolute path to the project root.
    """
    raise NotImplementedError
