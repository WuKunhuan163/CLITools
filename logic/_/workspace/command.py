"""Workspace management commands.

Handles TOOL --create-workspace, --open-workspace, --close-workspace,
--delete-workspace, --list-workspaces, --workspace.
"""

from logic._._ import EcoCommand


class WorkspaceCommand(EcoCommand):
    name = "workspace"
    usage = "TOOL --workspace | --create-workspace <path> | --list-workspaces"

    def handle(self, args, action="status"):
        """Dispatch to the appropriate workspace action."""
        from interface.workspace import get_workspace_manager
        from interface.status import fmt_status, fmt_detail, fmt_info

        wm = get_workspace_manager(self.project_root)

        handler = {
            "create": self._create,
            "open": self._open,
            "close": self._close,
            "delete": self._delete,
            "list": self._list,
            "status": self._status,
        }.get(action)

        if handler:
            handler(wm, args)
        else:
            self.error(f"Unknown workspace action: {action}")
        return 0

    def _create(self, wm, args):
        from interface.status import fmt_status, fmt_detail, fmt_info

        target_path = args[0] if args else None
        bp_type = None
        name = None
        i = 1
        while i < len(args):
            if args[i] == "--type" and i + 1 < len(args):
                bp_type = args[i + 1]
                i += 2
            elif args[i] == "--name" and i + 1 < len(args):
                name = args[i + 1]
                i += 2
            else:
                i += 1

        if not target_path:
            try:
                from tool.FILEDIALOG.interface.main import select_directory
                target_path = select_directory(title="Select workspace directory")
                if not target_path:
                    print(fmt_status("Cancelled.", style="error"))
                    return
            except ImportError:
                print(fmt_status("No path provided.", style="error"))
                print(fmt_detail("Usage: TOOL --create-workspace <path> [--type <blueprint>] [--name <name>]"))
                return

        try:
            info = wm.create_workspace(target_path, name=name, blueprint_type=bp_type)
            print(fmt_status("Workspace created."))
            print(fmt_detail(f"ID: {info['id']}"))
            print(fmt_detail(f"Path: {info['path']}"))
            print(fmt_detail(f"Blueprint: {info['blueprint_type']}"))
            print(fmt_info(f"Open: TOOL --open-workspace {info['id']}"))
        except FileExistsError as e:
            print(fmt_status("Already exists.", style="error"))
            print(fmt_detail(str(e)))
        except FileNotFoundError as e:
            print(fmt_status("Not found.", style="error"))
            print(fmt_detail(str(e)))

    def _open(self, wm, args):
        from interface.status import fmt_status, fmt_detail

        ws_id = args[0] if args else None
        if not ws_id:
            print(fmt_status("No workspace ID.", style="error"))
            print(fmt_detail("Usage: TOOL --open-workspace <workspace_id>"))
            return
        try:
            info = wm.open_workspace(ws_id)
            print(fmt_status("Workspace opened."))
            print(fmt_detail(f"Name: {info['name']}"))
            print(fmt_detail(f"Path: {info['path']}"))
        except FileNotFoundError as e:
            print(fmt_status("Not found.", style="error"))
            print(fmt_detail(str(e)))

    def _close(self, wm, args):
        from interface.status import fmt_status

        info = wm.close_workspace()
        if info:
            print(fmt_status("Workspace closed."))
        else:
            print(fmt_status("No active workspace."))

    def _delete(self, wm, args):
        from interface.status import fmt_status, fmt_detail

        ws_id = args[0] if args else None
        if not ws_id:
            print(fmt_status("No workspace ID.", style="error"))
            print(fmt_detail("Usage: TOOL --delete-workspace <workspace_id>"))
            return
        try:
            wm.delete_workspace(ws_id)
            print(fmt_status("Workspace deleted."))
            print(fmt_detail(f"ID: {ws_id}"))
        except FileNotFoundError as e:
            print(fmt_status("Not found.", style="error"))
            print(fmt_detail(str(e)))

    def _list(self, wm, args):
        from interface.status import fmt_status, fmt_detail

        workspaces = wm.list_workspaces()
        if not workspaces:
            print(fmt_status("No workspaces."))
            print(fmt_detail("Create one: TOOL --create-workspace <path>"))
            return
        print(f"{self.BOLD}Workspaces ({len(workspaces)}){self.RESET}\n")
        for ws in workspaces:
            marker = f" {self.GREEN}(active){self.RESET}" if ws.get("active") else ""
            status = ws.get("status", "closed")
            print(f"  {self.BOLD}{ws['name']}{self.RESET}{marker}  {self.DIM}[{status}]{self.RESET}")
            print(f"    {self.DIM}ID: {ws['id']}  Path: {ws['path']}{self.RESET}")
            print(f"    {self.DIM}Blueprint: {ws.get('blueprint_type', 'default')}{self.RESET}")
        print()

    def _status(self, wm, args):
        from interface.status import fmt_detail, fmt_status

        info = wm.active_workspace_info()
        if info:
            print(f"{self.BOLD}Active Workspace{self.RESET}")
            print(fmt_detail(f"Name: {info['name']}"))
            print(fmt_detail(f"ID: {info['id']}"))
            print(fmt_detail(f"Path: {info['path']}"))
            print(fmt_detail(f"Blueprint: {info.get('blueprint_type', 'default')}"))
            print(fmt_detail(f"Status: {info.get('status', 'unknown')}"))
        else:
            print(fmt_status("No active workspace."))
            print(fmt_detail("Using default scope (AITerminalTools root)."))
