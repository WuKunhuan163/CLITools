# CURL

Lightweight HTTP request tool using stdlib only. No external dependencies.

## Commands

```bash
CURL get "https://example.com"
CURL get "https://api.example.com/data" --headers '{"Authorization": "Bearer tok"}'
CURL post "https://api.example.com" --data '{"key": "value"}'
CURL put "https://api.example.com/item/1" --data '{"name": "updated"}'
CURL delete "https://api.example.com/item/1"
CURL head "https://example.com"
```

## Purpose

Provides a standardized HTTP client for agents. Supports GET, POST, PUT, DELETE, HEAD, PATCH with custom headers and JSON body. JSON responses are auto-formatted.
