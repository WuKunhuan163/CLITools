# runtime/_/ — Symmetric Command Runtime State

Git-tracked runtime state for symmetric CLI command groups.

## Structure

| Directory | Command Group | Contents |
|-----------|--------------|----------|
| `eco/brain/` | `--eco` / `BRAIN` | Brain state, tasks, context, session exports |
| `eco/experience/` | `--eco` / Experience | Lessons, tool experience, daily logs |

## Convention

Each subdirectory corresponds to a symmetric command group in `logic/_/`.
The `eco/` namespace groups brain and experience systems under the ecosystem command.
