# iCloud Logic — Technical Reference

## gui/login.py

`ICloudLoginWindow(TwoStepLoginWindow)`:
- Customized two-step login window for iCloud
- Inherits from `interface.gui.TwoStepLoginWindow`
- Handles Apple ID + password + 2FA verification code

## local/photos.py

`LocalPhotosLibrary`:
- Reads macOS Photos.app SQLite database (`Photos.sqlite`)
- Maps iCloud photo IDs to local file paths
- Caches UUID-to-path mappings for performance
- Accesses `originals/` directory for full-resolution files

## Gotchas

1. **macOS only**: `LocalPhotosLibrary` reads Photos.app's internal SQLite database, only available on macOS.
2. **Database locking**: Photos.app may lock the database during sync. Use read-only connections.
3. **Pickle usage**: `gui/login.py` imports pickle — session cookies may be serialized.
