# `TOOL dev sync` Mechanism and Work Loss Prevention

The `TOOL dev sync` command is designed to synchronize the `dev`, `tool`, `main`, and `test` branches in a specific, non-destructive manner. The primary goal is to ensure that the `dev` branch's state is propagated to `tool`, `main`, and `test` while preserving local development data and preventing accidental work loss.

## Branches Involved:
- **`dev`**: The primary development branch where active work is done. It can contain untracked files, local caches, and work-in-progress.
- **`tool`**: A branch that mirrors `dev` but is intended to contain only the tool-related code and resources, excluding development-specific files.
- **`main`**: A clean, stable branch representing the core framework, without any tool-specific code or development artifacts.
- **`test`**: A branch identical to `tool`, used for running automated tests.

## Synchronization Steps (`_dev_sync` function in `main.py`):

The `_dev_sync` function orchestrates the synchronization through a series of `TuringStage` operations, ensuring progress is displayed and errors are handled.

1.  **Commit Local Changes on `dev`**:
    -   **Action**: Before any branch switching or cleaning, `_dev_sync` attempts to automatically commit any uncommitted changes on the current branch (which is typically `dev`). This prevents local work from being lost during subsequent operations.
    -   **Mechanism**: `git add -A` followed by `git commit -m "Auto-commit before sync on '{start_branch}'"`.

2.  **Align `tool` from `dev` (Preserving Resources)**:
    -   **Action**: The `tool` branch is updated to match the `dev` branch, but with a critical difference: the `logic/_/install/` directory from `origin/tool` is explicitly preserved. This is crucial for tools like `PYTHON` that manage large binary assets via Git LFS in the `logic/_/install/` directory.
    -   **Mechanism**: This is achieved using a **Side-Index Git Operation**.
        -   A temporary Git index (`.git/index_sync_tool`) is used.
        -   The `dev` branch's tree is written to this temporary index.
        -   The `logic/_/install/` directory from `origin/tool` is then read into this same temporary index, effectively merging `dev`'s content with `origin/tool`'s `logic/_/install/`.
        -   A new commit is created from this merged tree on the `tool` branch.
        -   The `refs/heads/tool` is updated to point to this new commit.
    -   **Work Loss Prevention**: By using a side-index and explicitly preserving `origin/tool:resource`, local `logic/_/install/` content (which might be large LFS files) is not overwritten or deleted, and the `tool` branch's history remains consistent with its intended purpose.

3.  **Align `main` from `tool` (Framework Only)**:
    -   **Action**: The `main` branch is updated to reflect the `tool` branch, but it is stripped of all tool-specific code and development artifacts. This ensures `main` remains a clean representation of the core framework.
    -   **Mechanism**: Another **Side-Index Git Operation** is used.
        -   A temporary Git index (`.git/index_sync_main`) is used.
        -   The `tool` branch's tree is written to this temporary index.
        -   Specific "restricted" folders (`tool`, `logic/_/install`, `data`, `tmp`, `bin`) are explicitly removed from this temporary index using `git rm -rf --cached --ignore-unmatch`. This removes them from Git's tracking for the `main` branch but leaves them on disk as untracked files, preventing accidental deletion of local development data.
        -   A new commit is created from this stripped tree on the `main` branch.
        -   The `refs/heads/main` is updated to point to this new commit.
    -   **Work Loss Prevention**: `git rm --cached` is used instead of `rm -rf` to ensure that these directories are only removed from Git's index for the `main` branch, not from the local filesystem. This prevents deletion of local `tool/` directories, `data/`, `logic/_/install/`, etc., which are essential for `dev` branch development.

4.  **Align `test` from `tool`**:
    -   **Action**: The `test` branch is made identical to the `tool` branch.
    -   **Mechanism**: The `test` branch's reference is simply updated to point to the same commit as the `tool` branch.
    -   **Work Loss Prevention**: This step is a direct reference update and does not involve `git clean` or `rmtree` operations that could cause data loss.

5.  **Restore Original Branch**:
    -   **Action**: After all synchronization steps, the system checks out to the branch that was active when `_dev_sync` was initiated.
    -   **Mechanism**: `git checkout -f {start_branch}`.
    -   **Work Loss Prevention**: Ensures the developer is returned to their original working context.

## `.gitignore` Configuration:

The `.gitignore` file is **auto-generated** by `GitIgnoreManager` (`logic/git/manager.py`). Never edit it directly — modify `GitIgnoreManager.base_patterns` instead. It is crucial for preventing `git clean -fdx` from deleting important local development files. It is configured to explicitly ignore:
-   `/data/`: Root-level data directory (e.g., global config, audit reports).
-   `/logs/`: Root-level logs directory.
-   `/tmp/`: Root-level temporary files.
-   `/resource/`: Root-level resource directory (e.g., Python standalone builds managed by Git LFS).
-   `/tool/*/data/`: Data directories within individual tool folders.
-   `/tool/*/logs/`: Logs directories within individual tool folders.

This configuration ensures that `git clean -fdx` (which is used in `_run_installation_test` and other cleanup operations) will *not* remove these directories, preserving local caches and development-related files.

## Testing `TOOL dev sync` for Work Loss:

To test if `TOOL dev sync` still causes work loss, the following steps can be performed:

1.  **Create Local Changes**: Make some uncommitted changes in the `dev` branch, create new files in `tool/READ/data/`, and potentially modify a tool's `main.py` (e.g., `tool/USERINPUT/main.py`).
    -   **Example**: `touch tool/READ/data/test_file.txt`
    -   **Example**: `echo "# Test Change" >> tool/USERINPUT/main.py`
2.  **Run `TOOL dev sync`**: Execute the command.
3.  **Verify State**:
    -   Check if the uncommitted changes on `dev` were auto-committed.
    -   Verify that `tool/READ/data/` and its contents are still present.
    -   Check if `tool/USERINPUT/main.py` is still present and its content is as expected.
    -   Ensure `bin/USERINPUT` and `bin/DRAW` symlinks are still present and functional.
    -   Check `tool/PYTHON/data/install/` to ensure Python installations are intact.

The current implementation of `_dev_sync` and the `.gitignore` configuration are designed to prevent work loss by:
-   Auto-committing local changes on the starting branch.
-   Using side-index operations for `tool` and `main` branches to avoid direct checkouts and destructive `git clean` operations on the working directory.
-   Explicitly excluding `tool/`, `data/`, `bin/`, and `logic/config/tool_config_manager.py` from `git clean -fd` operations on the `test` branch during `_run_installation_test`.
-   Using `git rm --cached` for restricted folders on the `main` branch, which removes them from Git's tracking but keeps them on disk.

This comprehensive approach aims to make `TOOL dev sync` a safe and reliable operation for maintaining branch consistency without sacrificing local development progress.
