        # INKSCAPE — Agent Guide

        ## Source

        Migrated from [CLI-Anything/inkscape](https://github.com/HKUDS/CLI-Anything/tree/main/inkscape).

        **Status**: Draft — upstream code in `data/upstream/CLI-Anything/`.

        ## Architecture

        ```
        INKSCAPE/
          main.py              # Ecosystem wrapper (delegates to upstream CLI)
          tool.json            # Tool metadata
          data/upstream/       # Raw CLI-Anything harness code
          logic/               # (empty — to be developed)
          interface/           # (empty — to be developed)
        ```

        ## Commands (from upstream)

        | Command | Description |
        |---------|-------------|
        | document new | (upstream) |
| document open | (upstream) |
| document save | (upstream) |
| document info | (upstream) |
| document profiles | (upstream) |
| document canvas-size | (upstream) |
| document units | (upstream) |
| document json | (upstream) |
| gradient add-linear | (upstream) |
| gradient add-radial | (upstream) |
| gradient apply | (upstream) |
| gradient list | (upstream) |
| layer add | (upstream) |
| layer remove | (upstream) |
| layer move-object | (upstream) |

        ## Post-Processing Required

        1. Move core logic from `data/upstream/` into `logic/`
        2. Rewrite main.py with argparse (replace Click)
        3. Create `interface/main.py` for cross-tool API
        4. Add localization via `_()` helper
        5. Write ecosystem-style tests in `test/`
        6. Remove Click dependency if possible
