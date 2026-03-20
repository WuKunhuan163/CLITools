        # GIMP — Agent Guide

        ## Source

        Migrated from [CLI-Anything/gimp](https://github.com/HKUDS/CLI-Anything/tree/main/gimp).

        **Status**: Draft — upstream code in `data/upstream/CLI-Anything/`.

        ## Architecture

        ```
        GIMP/
          main.py              # Ecosystem wrapper (delegates to upstream CLI)
          tool.json            # Tool metadata
          data/upstream/       # Raw CLI-Anything harness code
          logic/               # (empty — to be developed)
          interface/           # (empty — to be developed)
        ```

        ## Commands (from upstream)

        | Command | Description |
        |---------|-------------|
        | canvas info | (upstream) |
| canvas resize | (upstream) |
| canvas scale | (upstream) |
| canvas crop | (upstream) |
| canvas mode | (upstream) |
| canvas dpi | (upstream) |
| draw text | (upstream) |
| draw rect | (upstream) |
| layer new | (upstream) |
| layer add-from-file | (upstream) |
| layer list | (upstream) |
| layer remove | (upstream) |
| layer duplicate | (upstream) |
| layer move | (upstream) |
| layer set | (upstream) |

        ## Post-Processing Required

        1. Move core logic from `data/upstream/` into `logic/`
        2. Rewrite main.py with argparse (replace Click)
        3. Create `interface/main.py` for cross-tool API
        4. Add localization via `_()` helper
        5. Write ecosystem-style tests in `test/`
        6. Remove Click dependency if possible
