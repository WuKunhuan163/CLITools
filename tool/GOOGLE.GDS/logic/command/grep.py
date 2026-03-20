#!/usr/bin/env python3
"""GDS grep command: search for patterns in remote files."""
import re
import sys


def execute(tool, args, state_mgr, load_logic, unknown=None, **kwargs):
    utils = load_logic("utils")

    grep_args = unknown or []
    if not grep_args:
        print("grep: missing operand", file=sys.stderr)
        return 1

    if "--help" in grep_args or "-h" in grep_args:
        _show_help()
        return 0

    case_insensitive = False
    count_only = False
    invert = False
    positional = []

    for a in grep_args:
        if a == "-i":
            case_insensitive = True
        elif a == "-c":
            count_only = True
        elif a == "-v":
            invert = True
        else:
            positional.append(a)

    if len(positional) == 0:
        print("grep: missing operand", file=sys.stderr)
        return 1
    elif len(positional) == 1:
        # Single arg: treat as filename, no pattern (show entire file with line numbers)
        pattern = None
        filenames = [positional[0]]
    else:
        pattern = positional[0]
        filenames = positional[1:]

    # Strip surrounding quotes from pattern
    if pattern:
        if (pattern.startswith('"') and pattern.endswith('"')) or \
           (pattern.startswith("'") and pattern.endswith("'")):
            pattern = pattern[1:-1]

    has_matches = False
    has_errors = False
    multi_file = len(filenames) > 1

    for filename in filenames:
        folder_id, fname, display = utils.resolve_file_path(
            tool.project_root, filename, state_mgr, load_logic
        )
        if not folder_id:
            print(f"grep: {filename}: {fname}", file=sys.stderr)
            has_errors = True
            continue

        ok, data = utils.read_file_via_api(tool.project_root, folder_id, fname)
        if not ok:
            print(f"grep: {filename}: {data.get('error', 'Cannot read file')}", file=sys.stderr)
            has_errors = True
            continue

        content = data.get("content", "")
        lines = content.split('\n')
        total = len(lines)
        width = len(str(total))

        if not pattern:
            # No pattern: display file with line numbers (like read)
            for i, line in enumerate(lines, 1):
                print(f"{i:{width}}: {line}")
            has_matches = True
            continue

        # Compile regex
        try:
            flags = re.IGNORECASE if case_insensitive else 0
            regex = re.compile(pattern, flags)
        except re.error as e:
            print(f"grep: invalid regex '{pattern}': {e}", file=sys.stderr)
            return 2

        match_count = 0
        for i, line in enumerate(lines, 1):
            found = regex.search(line)
            if (found and not invert) or (not found and invert):
                match_count += 1
                if not count_only:
                    prefix = f"{filename}:" if multi_file else ""
                    print(f"{prefix}{i:{width}}: {line}")

        if count_only:
            prefix = f"{filename}:" if multi_file else ""
            print(f"{prefix}{match_count}")

        if match_count > 0:
            has_matches = True

    if has_errors:
        return 2
    return 0 if has_matches else 1


def _show_help():
    print("""grep - search for patterns in remote files

Usage:
  GDS grep <pattern> <file> [file2 ...] [options]
  GDS grep <file>                         Display file with line numbers

Arguments:
  pattern                  Regex pattern to search for
  file                     Remote file path(s)

Options:
  -i                       Case-insensitive search
  -c                       Count matching lines only
  -v                       Invert match (show non-matching lines)
  -h, --help               Show this help message

Examples:
  GDS grep 'import' ~/tmp/script.py       Find lines with 'import'
  GDS grep -i 'error' ~/logs/app.log      Case-insensitive search
  GDS grep -c 'TODO' ~/src/main.py        Count TODO occurrences
  GDS grep script.py                      Display entire file""")
