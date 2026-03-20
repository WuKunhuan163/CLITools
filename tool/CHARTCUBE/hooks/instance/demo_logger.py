"""Hook instance: demo_logger

Logs each demo countdown tick to the session log.

Event: on_demo_action
"""
from interface.hooks import HookInstance


class DemoLogger(HookInstance):
    name = "demo_logger"
    description = "Log demo countdown ticks to the session log."
    event_name = "on_demo_action"
    enabled_by_default = False

    def execute(self, **kwargs):
        tool = kwargs.get("tool")
        countdown = kwargs.get("countdown", 0)
        if tool:
            tool.log(f"Demo countdown: {countdown}")
        return {"logged": True, "countdown": countdown}
