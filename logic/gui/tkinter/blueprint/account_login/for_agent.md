# For Agents: Account Login Blueprint

## Core Concepts
The `AccountLoginWindow` is a standard single-step login GUI requiring an account (email/ID) and a password.

## Key Fields (Interface I Data)
- `account`: The account identifier (e.g., Apple ID, email).
- `password`: The password.
- `status`: "success", "error", or "cancelled".
- `data`: On success, contains `account` and `password`. On error/cancel, contains full verification history.

## Verification Handler
Pass a `verify_handler(state)` function to the constructor.
- **Input**: `state` dict with `account` and `password`.
- **Expected Output**:
  - `{"status": "success", "data": {...}}`: Login successful.
  - `{"status": "error", "message": "..."}`: Login failed. The GUI will handle the retry count and display the error.

## Customization
Override `setup_ui` or provide initial values:
- `account_initial`: Pre-fill the account field.
- `error_msg`: Initial error message to display.

## Error Format
The GUI automatically formats errors as: `Attempt a/b: {message}`.
Max attempts defaults to 5.

