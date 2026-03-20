        # COMFYUI — Agent Guide

        ## Source

        Migrated from [CLI-Anything/comfyui](https://github.com/HKUDS/CLI-Anything/tree/main/comfyui).

        **Status**: Draft — upstream code in `data/upstream/CLI-Anything/`.

        ## Architecture

        ```
        COMFYUI/
          main.py              # Ecosystem wrapper (delegates to upstream CLI)
          tool.json            # Tool metadata
          data/upstream/       # Raw CLI-Anything harness code
          logic/               # (empty — to be developed)
          interface/           # (empty — to be developed)
        ```

        ## Commands (from upstream)

        | Command | Description |
        |---------|-------------|
        | images list | (upstream) |
| images download | (upstream) |
| images download-all | (upstream) |
| models checkpoints | (upstream) |
| models loras | (upstream) |
| models vaes | (upstream) |
| models controlnets | (upstream) |
| models node-info | (upstream) |
| models list-nodes | (upstream) |
| queue prompt | (upstream) |
| queue status | (upstream) |
| queue clear | (upstream) |
| queue history | (upstream) |
| queue interrupt | (upstream) |
| system stats | (upstream) |

        ## Post-Processing Required

        1. Move core logic from `data/upstream/` into `logic/`
        2. Rewrite main.py with argparse (replace Click)
        3. Create `interface/main.py` for cross-tool API
        4. Add localization via `_()` helper
        5. Write ecosystem-style tests in `test/`
        6. Remove Click dependency if possible
