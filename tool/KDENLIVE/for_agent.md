        # KDENLIVE — Agent Guide

        ## Source

        Migrated from [CLI-Anything/kdenlive](https://github.com/HKUDS/CLI-Anything/tree/main/kdenlive).

        **Status**: Draft — upstream code in `data/upstream/CLI-Anything/`.

        ## Architecture

        ```
        KDENLIVE/
          main.py              # Ecosystem wrapper (delegates to upstream CLI)
          tool.json            # Tool metadata
          data/upstream/       # Raw CLI-Anything harness code
          logic/               # (empty — to be developed)
          interface/           # (empty — to be developed)
        ```

        ## Commands (from upstream)

        | Command | Description |
        |---------|-------------|
        | export xml | (upstream) |
| export presets | (upstream) |
| guide add | (upstream) |
| guide remove | (upstream) |
| guide list | (upstream) |
| project new | (upstream) |
| project open | (upstream) |
| project save | (upstream) |
| project info | (upstream) |
| project profiles | (upstream) |
| project json | (upstream) |
| session status | (upstream) |
| session undo | (upstream) |
| session redo | (upstream) |
| session history | (upstream) |

        ## Post-Processing Required

        1. Move core logic from `data/upstream/` into `logic/`
        2. Rewrite main.py with argparse (replace Click)
        3. Create `interface/main.py` for cross-tool API
        4. Add localization via `_()` helper
        5. Write ecosystem-style tests in `test/`
        6. Remove Click dependency if possible
