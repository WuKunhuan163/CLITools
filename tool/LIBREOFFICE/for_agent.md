        # LIBREOFFICE — Agent Guide

        ## Source

        Migrated from [CLI-Anything/libreoffice](https://github.com/HKUDS/CLI-Anything/tree/main/libreoffice).

        **Status**: Draft — upstream code in `data/upstream/CLI-Anything/`.

        ## Architecture

        ```
        LIBREOFFICE/
          main.py              # Ecosystem wrapper (delegates to upstream CLI)
          tool.json            # Tool metadata
          data/upstream/       # Raw CLI-Anything harness code
          logic/               # (empty — to be developed)
          interface/           # (empty — to be developed)
        ```

        ## Commands (from upstream)

        | Command | Description |
        |---------|-------------|
        | calc add-sheet | (upstream) |
| calc remove-sheet | (upstream) |
| calc rename-sheet | (upstream) |
| calc set-cell | (upstream) |
| calc get-cell | (upstream) |
| calc list-sheets | (upstream) |
| document new | (upstream) |
| document open | (upstream) |
| document save | (upstream) |
| document info | (upstream) |
| document profiles | (upstream) |
| document json | (upstream) |
| impress add-slide | (upstream) |
| impress remove-slide | (upstream) |
| impress set-content | (upstream) |

        ## Post-Processing Required

        1. Move core logic from `data/upstream/` into `logic/`
        2. Rewrite main.py with argparse (replace Click)
        3. Create `interface/main.py` for cross-tool API
        4. Add localization via `_()` helper
        5. Write ecosystem-style tests in `test/`
        6. Remove Click dependency if possible
