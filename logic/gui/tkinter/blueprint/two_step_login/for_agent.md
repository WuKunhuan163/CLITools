# For Agents: Two-Step Login Blueprint

## Core Concepts
The `TwoStepLoginWindow` handles a two-stage login flow:
1. **Account Step**: User enters account. Handler checks if session reuse is possible or if password is needed.
2. **Password Step**: User enters password. Handler performs full authentication.

## Key Fields (Interface I Data)
- `account`: The account identifier.
- `password`: The password (only in step 2).
- `step`: Current stage ("account" or "password").
- `status`: "success", "error", or "cancelled".

## Verification Handler
Pass a `verify_handler(state)` function.
- **Input**: `state` dict with `account`, `password` (if any), and `step`.
- **Expected Output for step 'account'**:
  - `{"status": "success", "data": ...}`: Session reused, login complete.
  - `{"status": "need_password"}`: Transition to password step.
  - `{"status": "error", "message": "..."}`: Invalid account or other error.
- **Expected Output for step 'password'**:
  - `{"status": "success", "data": ...}`: Login successful.
  - `{"status": "error", "message": "..."}`: Authentication failed.

## UI Features
- **Prev Button**: Allows user to return from password step to account step.
- **Dynamic Button Text**: "Next" in account step, "Login" in password step.
- **Packing Order**: Account -> Password -> Error/Prompt.
- **Loading State**: "Verifying ..." for account, "Logging In ..." for password.

## Attempt Counting
- `attempt_count` only increments during the `password` step.
- Failed `account` checks show the error but do not increment the login retry counter.

