"""Task execution pipeline for OPENCLAW.

Orchestrates the loop:
  user task -> package state -> send to remote agent -> 
  receive response -> parse -> execute commands -> 
  package results -> send back -> ... until termination.
"""
import time
import threading
from typing import Optional, Callable

from tool.OPENCLAW.logic.chrome import api as yuanbao
from tool.OPENCLAW.logic.sandbox import execute_command, get_project_summary
from tool.OPENCLAW.logic.protocol import (
    build_system_prompt, build_task_message, build_feedback_message,
    parse_structured_tool_calls,
)
from tool.OPENCLAW.logic.session import SessionManager, Session


MAX_ITERATIONS = 50
RESPONSE_TIMEOUT = 180
HEARTBEAT_INTERVAL = 300  # seconds between heartbeat checks
LOOP_DETECTION_THRESHOLD = 3  # break after N identical responses


class Pipeline:
    """Manages one task execution loop."""

    def __init__(self, session_mgr: SessionManager, session: Session,
                 on_message: Optional[Callable] = None,
                 on_status: Optional[Callable] = None,
                 on_title: Optional[Callable] = None,
                 cdp_port: int = 9222):
        self.session_mgr = session_mgr
        self.session = session
        self.on_message = on_message or (lambda role, text: None)
        self.on_status = on_status or (lambda text: None)
        self.on_title = on_title or (lambda title: None)
        self.cdp_port = cdp_port
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._iteration = 0
        self._last_heartbeat = 0.0
        self._heartbeat_thread: Optional[threading.Thread] = None

    def start(self, user_task: str):
        """Start the pipeline in a background thread."""
        self._running = True
        self._last_heartbeat = time.time()
        self._thread = threading.Thread(
            target=self._run, args=(user_task,), daemon=True
        )
        self._thread.start()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True
        )
        self._heartbeat_thread.start()

    def stop(self):
        """Signal the pipeline to stop."""
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def _heartbeat_loop(self):
        """Periodic self-check while pipeline is running.

        Inspired by OpenClaw's heartbeat system: monitors remote agent
        responsiveness and task health between iterations.
        """
        while self._running:
            time.sleep(30)
            if not self._running:
                break

            elapsed = time.time() - self._last_heartbeat
            if elapsed >= HEARTBEAT_INTERVAL:
                self._last_heartbeat = time.time()
                try:
                    auth = yuanbao.get_auth_state(self.cdp_port)
                    if not auth.get("ok") or not auth.get("authenticated"):
                        self._emit_status("Heartbeat: Remote agent connection lost")
                        self._emit_message("system",
                            "Heartbeat check: Remote agent connection may be lost. "
                            "Verify that yuanbao.tencent.com is still open and logged in.")
                except Exception:
                    pass

    def _emit_message(self, role: str, content: str, **kwargs):
        self.session_mgr.add_message(self.session.id, role, content, **kwargs)
        self.on_message(role, content)

    def _emit_status(self, text: str):
        self.on_status(text)

    def _run(self, user_task: str):
        """Main pipeline loop."""
        try:
            self._emit_status("Booting remote agent connection...")

            # Pre-flight: ensure Yuanbao tab exists and is authenticated
            boot_result = yuanbao.boot_yuanbao(self.cdp_port)
            if not boot_result.get("ok"):
                error = boot_result.get("error", "Unknown error")
                self._emit_message("system", f"Boot failed: {error}")
                self._emit_status("Boot failed.")
                self._running = False
                return

            if not boot_result.get("authenticated"):
                self._emit_message("system",
                    "Yuanbao tab opened but not logged in. Please log in at yuanbao.tencent.com/chat.")
                self._emit_status("Waiting for login...")
                self._running = False
                return

            # Create new conversation on remote
            self._emit_status("Creating new conversation on remote agent...")
            create_result = yuanbao.create_conversation(self.cdp_port)
            if not create_result.get("ok"):
                self._emit_message("system",
                    f"Failed to create conversation: {create_result.get('error', 'unknown')}")
                self._emit_status("Failed to create conversation.")
                self._running = False
                return

            time.sleep(2)

            # Build and send the initial system prompt + task
            project_summary = get_project_summary()
            system_prompt = build_system_prompt(project_summary)
            task_msg = build_task_message(user_task)
            full_initial = f"{system_prompt}\n\n---\n\n{task_msg}"

            self._emit_message("user", user_task)
            self._emit_status("Sending task to remote agent...")

            send_result = yuanbao.send_message(full_initial, self.cdp_port)
            if not send_result.get("ok"):
                self._emit_message("system",
                    f"Failed to send message: {send_result.get('error', 'unknown')}")
                self._running = False
                return

            # Main loop
            is_first_response = True
            prev_response_text = ""
            repeat_count = 0
            response_count = yuanbao._count_responses(self.cdp_port)

            while self._running and self._iteration < MAX_ITERATIONS:
                self._iteration += 1
                self._emit_status(f"Waiting for agent response (iteration {self._iteration})...")

                resp = yuanbao.wait_for_response(
                    timeout=RESPONSE_TIMEOUT, port=self.cdp_port,
                    prev_response_count=response_count,
                )

                if not resp.get("ok") or not resp.get("text"):
                    self._emit_message("system", "No response received from agent.")
                    break

                self._last_heartbeat = time.time()
                response_text = resp["text"]
                response_count = resp.get("response_count", response_count)

                # Loop detection: break if agent repeats itself
                if response_text == prev_response_text:
                    repeat_count += 1
                    if repeat_count >= LOOP_DETECTION_THRESHOLD:
                        self._emit_message("system",
                            f"Agent stuck in loop ({repeat_count} identical responses). "
                            "Injecting correction...")
                        correction = (
                            "IMPORTANT: You are repeating yourself. "
                            "Your previous approach is not working. "
                            "Try a DIFFERENT command. "
                            "Use --openclaw-tool-help to discover available project tools."
                        )
                        yuanbao.send_message(correction, self.cdp_port)
                        repeat_count = 0
                        response_count = yuanbao._count_responses(self.cdp_port)
                        time.sleep(1)
                        continue
                else:
                    repeat_count = 0
                prev_response_text = response_text

                tool_calls = []  # TODO: extract from API response
                parsed = parse_structured_tool_calls(
                    response_text, tool_calls)

                if is_first_response and parsed.get("title"):
                    self.session_mgr.update_title(self.session.id, parsed["title"])
                    self.on_title(parsed["title"])
                    is_first_response = False
                elif is_first_response:
                    auto_title = response_text[:40].strip().split("\n")[0]
                    if auto_title:
                        self.session_mgr.update_title(self.session.id, auto_title)
                        self.on_title(auto_title)
                    is_first_response = False

                thoughts = [s["content"] for s in parsed["segments"]
                            if s["type"] == "thought"]
                if thoughts:
                    self._emit_message("assistant", "\n".join(thoughts))

                for seg in parsed["segments"]:
                    if seg["type"] == "experience":
                        self._emit_message(
                            "system",
                            f"[Experience recorded] {seg['content']}")

                if parsed.get("complete"):
                    self._emit_message("system", "Task completed by agent.")
                    self._emit_status("Task completed.")
                    self.session_mgr.complete_session(self.session.id)
                    break

                commands = [s["content"] for s in parsed["segments"]
                            if s["type"] == "command"]
                if not commands:
                    self._emit_status("Agent response received (no commands).")
                    break

                feedback_parts = []
                for cmd in commands:
                    self._emit_status(f"Executing: {cmd}")
                    self._emit_message("system", f"[Executing] {cmd}")
                    result = execute_command(cmd)
                    feedback = build_feedback_message(cmd, result)
                    feedback_parts.append(feedback)

                    output_preview = result.get("output", result.get("error", ""))
                    if output_preview:
                        preview = output_preview[:200]
                        if len(output_preview) > 200:
                            preview += "..."
                        self._emit_message("feedback", preview)

                all_feedback = "\n\n".join(feedback_parts)
                all_feedback += "\n\nContinue with the task. Use tool calls or <<OPENCLAW_TASK_COMPLETE>> when done."
                self._emit_status("Sending results to agent...")
                send_result = yuanbao.send_message(all_feedback, self.cdp_port)
                if not send_result.get("ok"):
                    self._emit_message("system", "Failed to send feedback to agent.")
                    break

                response_count = yuanbao._count_responses(self.cdp_port)
                time.sleep(1)

            if self._iteration >= MAX_ITERATIONS:
                self._emit_message("system",
                    f"Reached maximum iterations ({MAX_ITERATIONS}). Stopping.")
                self._emit_status("Max iterations reached.")

        except Exception as e:
            self._emit_message("system", f"Pipeline error: {e}")
            self._emit_status(f"Error: {e}")
        finally:
            self._running = False
            self._emit_status("Pipeline stopped.")
