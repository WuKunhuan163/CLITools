        # BLENDER — Agent Guide

        ## Source

        Migrated from [CLI-Anything/blender](https://github.com/HKUDS/CLI-Anything/tree/main/blender).

        **Status**: Draft — upstream code in `data/upstream/CLI-Anything/`.

        ## Architecture

        ```
        BLENDER/
          main.py              # Ecosystem wrapper (delegates to upstream CLI)
          tool.json            # Tool metadata
          data/upstream/       # Raw CLI-Anything harness code
          logic/               # (empty — to be developed)
          interface/           # (empty — to be developed)
        ```

        ## Commands (from upstream)

        | Command | Description |
        |---------|-------------|
        | new | (upstream) |
| open | (upstream) |
| save | (upstream) |
| info | (upstream) |
| profiles | (upstream) |
| json | (upstream) |
| object | (upstream) |
| add | (upstream) |
| remove | (upstream) |
| duplicate | (upstream) |
| transform | (upstream) |
| set | (upstream) |
| list | (upstream) |
| get | (upstream) |
| create | (upstream) |

        ## Post-Processing Required

        1. Move core logic from `data/upstream/` into `logic/`
        2. Rewrite main.py with argparse (replace Click)
        3. Create `interface/main.py` for cross-tool API
        4. Add localization via `_()` helper
        5. Write ecosystem-style tests in `test/`
        6. Remove Click dependency if possible
