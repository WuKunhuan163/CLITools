"""Backend modules for the assistant GUI server.

Decomposed from the monolithic server.py into domain-specific mixins:

  keys.py       - API key validation, save, delete, reverify
  models.py     - Model listing, metadata, state, icon resolution, i18n, palette
  sandbox.py    - Sandbox policy and permission endpoints
  workspace.py  - Workspace management endpoints
  brain.py      - Brain instance management endpoints
  edits.py      - File edit and hunk management endpoints
  usage.py      - Usage data and currency endpoints
  config.py     - Session configuration persistence

  key.py        - KeyManagerWindow (tkinter GUI for API key management)
  store.py      - RoundStore for per-round token tracking + HTML renderers
"""

from logic.assistant.gui.backend.keys import KeysMixin
from logic.assistant.gui.backend.models import ModelsMixin
from logic.assistant.gui.backend.sandbox import SandboxMixin
from logic.assistant.gui.backend.workspace import WorkspaceMixin
from logic.assistant.gui.backend.brain import BrainMixin
from logic.assistant.gui.backend.edits import EditsMixin
from logic.assistant.gui.backend.usage import UsageMixin
from logic.assistant.gui.backend.config import ConfigMixin

__all__ = [
    "KeysMixin", "ModelsMixin", "SandboxMixin", "WorkspaceMixin",
    "BrainMixin", "EditsMixin", "UsageMixin", "ConfigMixin",
]
