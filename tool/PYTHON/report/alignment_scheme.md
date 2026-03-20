# Python Standalone Alignment Scheme

This document outlines the architecture and alignment strategy for the PYTHON proxy and manager tool.

## 1. Resource Architecture (Download Separation)
To keep the tool branches clean and ensure efficient deployment, we use a separated resource store:
    - **Resource Store**: `logic/_/install/resource/PYTHON/data/install/`
      - Contains full standalone Python builds (ZST/TAR) and their metadata.
      - Tracked in the `tool` branch.
    - **Local Installation**: `tool/PYTHON/data/install/`
      - Contains actual extracted Python environments.
  - Ignored by `.gitignore`.
  - Populated on-demand via `PYTHON --py-install <version>`.

## 2. Automated Sourcing (The Astral Alignment)
We align with the [python-build-standalone](https://github.com/astral-sh/python-build-standalone) project:
- **Manual Phase**: HTML scraping from release assets (legacy).
- **Automated Phase**: GitHub API integration.
  - Use `git ls-remote --tags` to identify all available release dates.
  - Use GitHub Release API to fetch asset metadata.
  - Automatically filter the latest maintenance release for each Python version.

## 3. Version Resolution Logic
- **Shorthand Support**: Users can use `@3.x` (e.g., `@3.8`) to specify a version.
- **Numeric Sorting**: Resolution is numeric-aware (`3.8.10` > `3.8.9`).
- **Dynamic Selection**: The tool automatically picks the latest installed patch version for the requested minor version.
- **System Mapping**: Automatically matches the host system tag (macos, linux64, windows-amd64, etc.) to the appropriate build.

## 4. Maintenance & Updates
    - **Resource Update (`PYTHON update`)**: Synchronizes our remote `logic/_/install` store with upstream releases.
      - **Remote Awareness**: Before migration, the tool checks the remote `tool` branch for existing resources to avoid redundant downloads and pushes.
      - **Download Isolation**: Assets are downloaded to `tmp/install/` with hashed directory names to avoid collisions.
  - **Git Migration**: Metadata (`PYTHON.json`) and binary resources are temporarily moved to `logic/_/install/` for committing to the `tool` branch.
  - **Zero-Footprint Local Repo**: After a successful `git push`, the local binary resource is immediately purged to keep the repository small.
  - **Automated Discovery**: Uses `git ls-remote --tags` and expanded asset HTML scraping for reliable release tracking.
- **Alignment Checks**: Audit logic ensures that installed versions match the official supported list in `tool.json`.
