# Gemini API Setup Guide

To use the vision analysis features in the `READ` tool, you need to configure a Google Gemini API key.

## 1. Obtain an API Key
1. Go to the [Google AI Studio](https://aistudio.google.com/).
2. Create a new API key.

## 2. Configure Environment Variables
You can set the API key in your shell profile (e.g., `.bashrc`, `.zshrc`) or a `.env` file in the project root.

The `READ` tool looks for the following variables:
- `GOOGLE_API_KEY_FREE`: Your free-tier API key.
- `GOOGLE_API_KEY_PAID`: Your paid-tier API key (optional, will fallback if free fails).

Example for `.zshrc`:
```bash
export GOOGLE_API_KEY_FREE="your_api_key_here"
```

## 3. Command Line Override
You can also specify the key directly when running the tool:
```bash
READ image.png --key "your_api_key_here"
```

## 4. Test Connection
To verify your setup, run:
```bash
READ --test-vision
```

