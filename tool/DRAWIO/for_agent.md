        # DRAWIO — Agent Guide

        ## Source

        Migrated from [CLI-Anything/drawio](https://github.com/HKUDS/CLI-Anything/tree/main/drawio).

        **Status**: Draft — upstream code in `data/upstream/CLI-Anything/`.

        ## Architecture

        ```
        DRAWIO/
          main.py              # Ecosystem wrapper (delegates to upstream CLI)
          tool.json            # Tool metadata
          data/upstream/       # Raw CLI-Anything harness code
          logic/               # (empty — to be developed)
          interface/           # (empty — to be developed)
        ```

        ## Commands (from upstream)

        | Command | Description |
        |---------|-------------|
        | connect add | (upstream) |
| connect remove | (upstream) |
| connect label | (upstream) |
| connect style | (upstream) |
| connect list | (upstream) |
| connect styles | (upstream) |
| export render | (upstream) |
| export formats | (upstream) |
| page add | (upstream) |
| page remove | (upstream) |
| page rename | (upstream) |
| page list | (upstream) |
| project new | (upstream) |
| project open | (upstream) |
| project save | (upstream) |

        ## Post-Processing Required

        1. Move core logic from `data/upstream/` into `logic/`
        2. Rewrite main.py with argparse (replace Click)
        3. Create `interface/main.py` for cross-tool API
        4. Add localization via `_()` helper
        5. Write ecosystem-style tests in `test/`
        6. Remove Click dependency if possible
