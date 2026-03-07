# iCloud Logic

iCloud account management. Provides GUI-based login (two-step verification) and local Photos library access.

## Structure

## Sub-Packages

| Directory | Purpose |
|-----------|---------|
| `gui/` | `ICloudLoginWindow` — Tkinter login GUI using `TwoStepLoginWindow` blueprint |
| `local/` | `LocalPhotosLibrary` — SQLite-based access to macOS Photos.app library |
