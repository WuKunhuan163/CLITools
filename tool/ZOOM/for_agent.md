        # ZOOM — Agent Guide

        ## Source

        Migrated from [CLI-Anything/zoom](https://github.com/HKUDS/CLI-Anything/tree/main/zoom).

        **Status**: Draft — upstream code in `data/upstream/CLI-Anything/`.

        ## Architecture

        ```
        ZOOM/
          main.py              # Ecosystem wrapper (delegates to upstream CLI)
          tool.json            # Tool metadata
          data/upstream/       # Raw CLI-Anything harness code
          logic/               # (empty — to be developed)
          interface/           # (empty — to be developed)
        ```

        ## Commands (from upstream)

        | Command | Description |
        |---------|-------------|
        | auth setup | (upstream) |
| auth login | (upstream) |
| auth status | (upstream) |
| auth logout | (upstream) |
| meeting create | (upstream) |
| meeting list | (upstream) |
| meeting info | (upstream) |
| meeting update | (upstream) |
| meeting delete | (upstream) |
| meeting join | (upstream) |
| meeting start | (upstream) |
| participant add | (upstream) |
| participant add-batch | (upstream) |
| participant list | (upstream) |
| participant remove | (upstream) |

        ## Post-Processing Required

        1. Move core logic from `data/upstream/` into `logic/`
        2. Rewrite main.py with argparse (replace Click)
        3. Create `interface/main.py` for cross-tool API
        4. Add localization via `_()` helper
        5. Write ecosystem-style tests in `test/`
        6. Remove Click dependency if possible
