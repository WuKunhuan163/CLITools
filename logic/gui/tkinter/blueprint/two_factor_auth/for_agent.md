# For Agents: Two-Factor Authentication (2FA) Blueprint

## Core Concepts
The `TwoFactorAuthWindow` provides a multi-box numeric entry for 2FA codes.

## Key Fields (Interface I Data)
- `status`: "success", "error", or "cancelled".
- `data`: On success, the N-digit code string. On error/cancel, contains full verification history.

## Parameters
- `n`: Number of digits (default 6).
- `allowed_chars`: Filter for allowed characters (default "0123456789").
- `prompt_msg`: Initial instruction/hint displayed below the boxes.

## Verification Handler
Pass a `verify_handler(code)` function.
- **Input**: `code` string.
- **Expected Output**:
  - `{"status": "success", "data": ...}`
  - `{"status": "error", "message": "..."}`

## UX Features
- **Auto-focus**: Moves focus to the next box on input and previous box on backspace.
- **Hidden Cursor**: Digit boxes do not show a cursor (`insertontime=0`).
- **Loading State**: Disables inputs and shows "Verifying..." during handler execution.

