# DUMMY2

DUMMY2 tool template.

## Ecosystem Support

This tool is part of the `TOOL` ecosystem, which provides:

- **Standalone Runtime**: Tools can specify a dependency on the `PYTHON` tool. The manager ensures they run in a dedicated, isolated Python environment.
- **Git LFS Support**: Managed via the root `.gitattributes`. Large files (models, binaries) are automatically tracked by Git LFS.
- **Automatic Persistence**: The system supports automatic pushes every three commits to protect work progress. This is managed by a `post-commit` hook in the root `.git/hooks`.
- **Shared Utilities**: Access core logic in the root `logic/` folder:
    - `logic.turing`: For building multi-stage workers with progress display (the "Turing Machine" pattern).
    - `logic.utils`: Shared terminal utilities, RTL support, and more.
    - `logic.tool.base`: Base class for standardized command handling (e.g., automated `setup` command support).
    - `logic.audit`: General-purpose audit and caching system.
- **Localization**: Built-in support for multiple languages in `logic/translation/`. Always use the `_()` helper for user-facing strings.
- **Unit Testing**: Standardized testing framework using `unittest`. Run tests in parallel with `TOOL test DUMMY2`.

## Development Guidelines

1. **Isolation**: Use the `PYTHON` tool dependency for a standalone runtime. Specify dependencies in `tool.json`.
2. **Testing**: Add unit tests in `test/`. Use `TOOL test DUMMY2` to run them in parallel.
3. **Translation**: English strings MUST be provided as default arguments within the code; **DO NOT include 'en' sections in translation JSON files**.
4. **Cleanliness**: Keep the `main` and `test` branches clean. Perform active development on the `dev` or `tool` branch.
