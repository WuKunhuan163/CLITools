"""GUI interface for tools.

Provides access to the GUI framework: blueprints, engine, manager, and styles.
"""
# TODO: [migration] This facade will be migrated/rewritten as part of the __/ architecture restructure.
from logic._.gui.tkinter.blueprint.button_bar.gui import ButtonBarWindow
from logic._.gui.tkinter.blueprint.tutorial.gui import TutorialWindow, TutorialStep
from logic._.gui.tkinter.blueprint.base import BaseGUIWindow, setup_common_bottom_bar
from logic._.gui.tkinter.blueprint.two_step_login.gui import TwoStepLoginWindow
from logic._.gui.tkinter.blueprint.two_factor_auth.gui import TwoFactorAuthWindow
from logic._.gui.tkinter.blueprint.bottom_bar.gui import BottomBarWindow, setup_bottom_bar
from logic._.gui.tkinter.blueprint.editable_list.gui import EditableListWindow
from logic._.gui.tkinter.style import get_label_style, get_button_style, get_gui_colors
from logic._.gui.engine import (
    setup_gui_environment,
    get_safe_python_for_gui,
    is_sandboxed,
    get_sandbox_type,
    play_notification_bell,
)
from logic._.gui.manager import run_gui_subprocess, handle_gui_remote_command
from logic._.gui.serve.html_server import LocalHTMLServer, find_free_port
from logic._.gui.tkinter.widget.text import UndoableText
from logic._.gui.html.blueprint.chatbot.server import ChatbotServer
from logic._.gui.tkinter.blueprint.chatbot.gui import ChatbotWindow

__all__ = [
    "ButtonBarWindow",
    "TutorialWindow",
    "TutorialStep",
    "BaseGUIWindow",
    "setup_common_bottom_bar",
    "BottomBarWindow",
    "setup_bottom_bar",
    "EditableListWindow",
    "TwoStepLoginWindow",
    "TwoFactorAuthWindow",
    "get_label_style",
    "get_button_style",
    "get_gui_colors",
    "setup_gui_environment",
    "get_safe_python_for_gui",
    "is_sandboxed",
    "get_sandbox_type",
    "play_notification_bell",
    "run_gui_subprocess",
    "handle_gui_remote_command",
    "LocalHTMLServer",
    "find_free_port",
    "UndoableText",
    "ChatbotServer",
    "ChatbotWindow",
]
