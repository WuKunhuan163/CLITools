# iCloudPD Tool Enhancement

## Current Status
- [x] Support local MacBook Photos Library (`.photoslibrary`).
- [x] Custom filename and directory grouping using placeholders.
- [x] Performance optimization for gathering stage using persistent cache (`full_record` in `photos_cache.json`).
- [x] Robust Ctrl+C (KeyboardInterrupt) handling with terminal restoration.
- [x] Download failure reporting above the status bar.
- [x] Fixed double-counting bug in download progress.

## Test Instructions
To test Ctrl+C handling:
1. Run `python3 /Applications/AITerminalTools/tmp/test_ptm_interrupt.py`
2. Press `Ctrl+C` during the sleep loop.
3. Verify that the "Operation cancelled by user." message appears in RED and the script exits to the shell immediately.

To test iCloudPD with the new preferences:
```bash
iCloudPD --apple-id 18876089955@139.com --local-photos ~/Desktop/Photos\ Library.photoslibrary --prefix "<YYYY><MM><DD>_<hh><mm><ss> · " --since 2024-10-01 --before 2024-10-31 --output /Applications/AITerminalTools/tmp/tmp_iCloudPD_photos/ --no-gui
```

## Logic Principle: Gathering Cache
The "Gathering" stage fetches full metadata (like download URLs) for assets not found locally.
- **Cache**: results are saved in `tool/iCloud.iCloudPD/data/scan/<id>/photos_cache.json` under `full_record`.
- **Fast Mode**: Subsequent runs skip iCloud lookups for any asset that has a `full_record` in the cache.
- **Override**: Use `--ignore-gather-cache` to force a refresh from iCloud.

## Keyboard Suppressor
- Uses `termios` to suppress echoing and line buffering during erasable status lines.
- **Reference Counted**: Safe for nested usage (e.g., PTM and WorkerPool).
- **SIGINT**: `ISIG` is kept enabled so `Ctrl+C` still triggers a `KeyboardInterrupt` signal naturally.
- **Cleanup**: Restores settings on exit, exception, or interrupt.
