# GUI Translation - Agent Guide

## Resolution Order

1. Tool-specific: `get_translation(internal_dir, key, default)` checks tool's translation dir
2. Shared GUI: Falls back to `logic/gui/translation` via `logic.lang.utils.get_translation`

## Common Keys (from blueprints)

| Key | Example Default |
|-----|-----------------|
| `time_remaining` | "Remaining:" |
| `time_added` | "Time added!" |
| `add_time` | "Add {seconds}s" |
| `btn_cancel` | "Cancel" |
| `btn_login` | "Login" |
| `btn_next` | "Next" |
| `btn_prev` | "Prev" |
| `btn_complete` | "Complete" |
| `btn_verify` | "Verify" |
| `btn_verifying` | "Verifying ..." |
| `btn_logging_in` | "Logging In ..." |
| `login_instruction` | "Please sign in" |
| `label_account` | "Account:" |
| `label_password` | "Password:" |
| `2fa_instruction` | "Enter the verification code" |
| `tutorial_step_count` | "Step {current}/{total}" |

## File Format

JSON object: `{"key": "value", "key_with_placeholder": "Text {name}"}`. Use UTF-8 encoding.
