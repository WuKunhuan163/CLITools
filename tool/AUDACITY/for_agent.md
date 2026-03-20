        # AUDACITY — Agent Guide

        ## Source

        Migrated from [CLI-Anything/audacity](https://github.com/HKUDS/CLI-Anything/tree/main/audacity).

        **Status**: Draft — upstream code in `data/upstream/CLI-Anything/`.

        ## Architecture

        ```
        AUDACITY/
          main.py              # Ecosystem wrapper (delegates to upstream CLI)
          tool.json            # Tool metadata
          data/upstream/       # Raw CLI-Anything harness code
          logic/               # (empty — to be developed)
          interface/           # (empty — to be developed)
        ```

        ## Commands (from upstream)

        | Command | Description |
        |---------|-------------|
        | clip import | (upstream) |
| clip add | (upstream) |
| clip remove | (upstream) |
| clip trim | (upstream) |
| clip split | (upstream) |
| clip move | (upstream) |
| clip list | (upstream) |
| label add | (upstream) |
| label remove | (upstream) |
| label list | (upstream) |
| media probe | (upstream) |
| media check | (upstream) |
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
