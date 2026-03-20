        # OBS — Agent Guide

        ## Source

        Migrated from [CLI-Anything/obs-studio](https://github.com/HKUDS/CLI-Anything/tree/main/obs-studio).

        **Status**: Draft — upstream code in `data/upstream/CLI-Anything/`.

        ## Architecture

        ```
        OBS/
          main.py              # Ecosystem wrapper (delegates to upstream CLI)
          tool.json            # Tool metadata
          data/upstream/       # Raw CLI-Anything harness code
          logic/               # (empty — to be developed)
          interface/           # (empty — to be developed)
        ```

        ## Commands (from upstream)

        | Command | Description |
        |---------|-------------|
        | project new | (upstream) |
| project open | (upstream) |
| project save | (upstream) |
| project info | (upstream) |
| project json | (upstream) |
| session status | (upstream) |
| session undo | (upstream) |
| session redo | (upstream) |
| session history | (upstream) |
| scene_group add | (upstream) |
| scene_group remove | (upstream) |
| scene_group duplicate | (upstream) |
| scene_group set-active | (upstream) |
| scene_group list | (upstream) |
| source_group add | (upstream) |

        ## Post-Processing Required

        1. Move core logic from `data/upstream/` into `logic/`
        2. Rewrite main.py with argparse (replace Click)
        3. Create `interface/main.py` for cross-tool API
        4. Add localization via `_()` helper
        5. Write ecosystem-style tests in `test/`
        6. Remove Click dependency if possible
