        # ANYGEN — Agent Guide

        ## Source

        Migrated from [CLI-Anything/anygen](https://github.com/HKUDS/CLI-Anything/tree/main/anygen).

        **Status**: Draft — upstream code in `data/upstream/CLI-Anything/`.

        ## Architecture

        ```
        ANYGEN/
          main.py              # Ecosystem wrapper (delegates to upstream CLI)
          tool.json            # Tool metadata
          data/upstream/       # Raw CLI-Anything harness code
          logic/               # (empty — to be developed)
          interface/           # (empty — to be developed)
        ```

        ## Commands (from upstream)

        | Command | Description |
        |---------|-------------|
        | config set | (upstream) |
| config get | (upstream) |
| config delete | (upstream) |
| config path | (upstream) |
| file upload | (upstream) |
| session status | (upstream) |
| session history | (upstream) |
| session undo | (upstream) |
| session redo | (upstream) |
| task create | (upstream) |
| task status | (upstream) |
| task poll | (upstream) |
| task download | (upstream) |
| task thumbnail | (upstream) |
| task run | (upstream) |

        ## Post-Processing Required

        1. Move core logic from `data/upstream/` into `logic/`
        2. Rewrite main.py with argparse (replace Click)
        3. Create `interface/main.py` for cross-tool API
        4. Add localization via `_()` helper
        5. Write ecosystem-style tests in `test/`
        6. Remove Click dependency if possible
