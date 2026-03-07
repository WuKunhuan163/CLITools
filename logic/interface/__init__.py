"""Unified interface layer for cross-tool communication and core access.

Provides two categories of interfaces:

1. **Facade modules** — re-export commonly used core components so that
   tools can use shorter, stable import paths instead of reaching deep
   into the internal package hierarchy:

       from logic.interface.turing import ProgressTuringMachine, TuringStage
       from logic.interface.gui    import ButtonBarWindow, TutorialWindow
       from logic.interface.config import get_color, get_setting
       from logic.interface.lang   import get_translation
       from logic.interface.tool   import ToolBase, ToolEngine

2. **Tool interface registry** — each installed tool may expose a
   ``logic/interface/main.py`` module with functions that other tools
   can call:

       from logic.interface import get_interface
       tavily = get_interface("TAVILY")
       if tavily:
           results = tavily.search("python best practices")
"""
from logic.interface.registry import get_interface, list_interfaces

__all__ = ["get_interface", "list_interfaces"]
