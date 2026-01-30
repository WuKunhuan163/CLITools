# READ

Read and extract content from PDF, Word, and images for AI analysis.

## Ecosystem Support

This tool is part of the `TOOL` ecosystem, which provides:

- **Standalone Runtime**: Tools can specify a dependency on the `PYTHON` tool. The manager ensures they run in a dedicated, isolated Python environment.
- **Git LFS Support**: Managed via the root `.gitattributes`. Large files (models, binaries) are automatically tracked by Git LFS.
- **Automatic Persistence**: The system supports automatic pushes every three commits to protect work progress.
- **Shared Utilities**: Access core logic in the root `logic/` folder.
- **Localization**: Built-in support for multiple languages in `logic/translation/`.
- **Unit Testing**: Standardized testing framework using `unittest`.

## Development Guidelines

1. **Isolation**: Use the `PYTHON` tool dependency for a standalone runtime. Specify dependencies in `tool.json`.
2. **Testing**: Add unit tests in `test/`. Use `TOOL test READ` to run them in parallel.
3. **Translation**: English strings MUST be provided as default arguments within the code.
4. **Cleanliness**: Keep the `main` and `test` branches clean. Perform active development on the `dev` or `tool` branch.
