# GOOGLE.GC -- For Agent Reference

## Quick Reference

### Cell Operations
```bash
GOOGLE.GC cell add [--cell-type code|text] [--text "content"]
GOOGLE.GC cell edit --index N [--clear] [--type "text"] [--clear-line L] [--line L --insert "text"] [--from-line M --to-line N --replace-with "new"]
GOOGLE.GC cell run --index N [--wait 120]
GOOGLE.GC cell delete [--index N]
GOOGLE.GC cell move --index N --direction up|down
```

### Runtime & Notebook
```bash
GOOGLE.GC runtime run-all|interrupt|restart
GOOGLE.GC notebook save|clear-outputs
```

## Key Behaviors

- All operations use CDMCP session `require_tab()` for tab lifecycle
- If the Colab tab is missing, it auto-opens in the session window
- If the session window is lost, triggers full session reboot
- Every operation shows MCP visual effects (lock, badge, highlight, counter)
- Turing machine tracks state for error recovery

## Cell Edit Details

- `--replace-with` escaping: `\\n` = literal `\n`, actual newline = line separator
- Line indices are 0-based
- Typing speed adapts to content length (more content = faster)
- Line-level highlighting for line operations

## Error Handling

- Missing cell: Turing machine reports "Cell N not found (have M cells)"
- Missing line: Reports "Line N not found (cell has M lines)"
- No Colab tab: Auto-opens if session exists, fails otherwise
- CDP unavailable: Reports connection error at first stage
