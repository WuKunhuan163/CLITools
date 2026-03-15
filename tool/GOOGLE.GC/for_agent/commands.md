# GOOGLE.GC Commands Reference

## Cell Operations
```bash
GOOGLE.GC cell add [--cell-type code|text] [--text "content"]
GOOGLE.GC cell edit --index N [--clear] [--type "text"] [--clear-line L] [--line L --insert "text"] [--from-line M --to-line N --replace-with "new"]
GOOGLE.GC cell run --index N [--wait 120]
GOOGLE.GC cell delete [--index N]
GOOGLE.GC cell move --index N --direction up|down
GOOGLE.GC cell focus --index N [--toolbar-click move-up|move-down|delete|edit|more] [--menu-click select|copy-link|cut|copy|delete|comment|editor-settings|mirror|scratch|form]
```

## Toolbar Buttons
```bash
GOOGLE.GC toolbar commands|add-code|add-text|run-all|run-dropdown|connect|settings|comments|toggle-header
```

## Top Bar Menus
```bash
GOOGLE.GC menu file|edit|view|insert|runtime|tools|help [--item "Menu item text"]
```

### Menu Items (use with --item)
- **File**: Locate in Drive, Open in playground mode, New notebook in Drive, Open notebook, Upload notebook, Rename, Move, Move to trash, Save a copy in Drive, Save a copy as a GitHub Gist, Save a copy in GitHub, Save, Save and pin revision, Revision history, Notebook info, Download, Print
- **Edit**: Undo, Redo, Select all cells, Cut, Copy, Paste, Find and replace, Find next, Find previous, Delete selected cells, Copy to clipboard
- **View**: Table of contents, Find and replace, Executed code history, Command palette, Show/hide code, Collapse sections
- **Insert**: Code cell, Text cell, Section header, Snippet
- **Runtime**: Run all, Run before, Run the focused cell, Run selection, Run cell and below, Interrupt execution, Restart session, Restart session and run all, Disconnect and delete runtime, Change runtime type, Manage sessions, View resources, View runtime logs
- **Tools**: Settings, Command palette, Keyboard shortcuts, Diff notebooks
- **Help**: Search the help, FAQ, Keyboard shortcuts

## Settings Dialog
```bash
GOOGLE.GC settings show [--tab Site|Editor|Miscellaneous]     # Show settings values
GOOGLE.GC settings set --tab Editor --pref pref_showLineNumbers  # Toggle a checkbox
GOOGLE.GC settings set --tab Site --pref pref_siteTheme --value dark  # Set a select
GOOGLE.GC settings save                                         # Save and close
GOOGLE.GC settings cancel                                       # Close without saving
```

### Available Preferences (--pref)
**Site**: `pref_siteTheme` (select: light/dark/adaptive), `pref_desktopNotifications` (checkbox), `pref_privateOutputsEnabledByDefault` (checkbox), `pref_tabbedUiLocation` (select: vertical/horizontal), `pref_emptyWelcomeNotebook` (checkbox)

**Editor**: `pref_editorColorizationLight` (select), `pref_editorKeyMap` (select: default/vim/classic), `pref_editorFontSize` (select), `pref_indentNumSpaces` (select: 2/4), `pref_editorAutoTriggerCompletions` (checkbox), `pref_showLineNumbers` (checkbox), `pref_showGuides` (checkbox), `pref_editorFolding` (checkbox), `pref_editorWrapping` (checkbox), `pref_autoCloseBrackets` (checkbox), `pref_editorAcceptSuggestionOnEnter` (checkbox), `pref_fontLigatures` (checkbox), `pref_lspDiagnostics` (select), `pref_inlineVariables` (select)

**Miscellaneous**: `pref_powerLevel` (select), `pref_corgiMode` (checkbox), `pref_kittyMode` (checkbox), `pref_crabMode` (checkbox)

## Runtime & Notebook
```bash
GOOGLE.GC runtime run-all|interrupt|restart
GOOGLE.GC notebook save|clear-outputs
```

## Sidebar
```bash
GOOGLE.GC sidebar toc|find|snippets|inspector|secrets|files|data-explorer
```

## Bottom Bar
```bash
GOOGLE.GC bottom variables|terminal
```

## State & Other
```bash
GOOGLE.GC state [--session ID] [--tab TAB] [--json]
GOOGLE.GC status
GOOGLE.GC inject "code" --timeout N
GOOGLE.GC reopen
GOOGLE.GC oauth
```
