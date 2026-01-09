# TODO: GDS Setup Process Development

## New Architecture Implementation
- [x] Create `setup.py` for project deployment (creates `TOOL` symlink).
- [x] Create `main.py` for tool management (`TOOL install`, `TOOL test`).
- [x] Migrate `USERINPUT` tool to the new structure.
  - [x] Created `USERINPUT/` folder.
  - [x] Moved entry point to `USERINPUT/main.py`.
  - [x] Organized internal structure (`proj/`, `data/`, `tool.json`).
- [ ] Migrate other tools (`GOOGLE_DRIVE`, `PYPI`, etc.) to the new structure.

## GDS Setup Wizard (New Branch)
- [x] Initial structure of GOOGLE_DRIVE --setup (Step 1: Service Account Verification).
- [x] Created `_PROJ` folders and `requirements.txt` for all tools.
- [ ] Implement Step 2 of Setup Wizard: Path Configuration.
- [ ] Implement Step 3 of Setup Wizard: Final Validation.
- [ ] Successfully run `GDS echo Hello`.



