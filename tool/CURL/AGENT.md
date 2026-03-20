# CURL -- Agent Reference

## Commands

```bash
CURL get URL                    # HTTP GET
CURL post URL --data '{"k":"v"}'  # HTTP POST with JSON body
CURL put URL --data '{"k":"v"}'   # HTTP PUT
CURL delete URL                 # HTTP DELETE
CURL head URL                   # HTTP HEAD (headers only)
CURL patch URL --data '...'     # HTTP PATCH
```

## Options

- `--headers '{"H":"V"}'` -- Custom request headers (JSON string)
- `--data '{"k":"v"}'` -- Request body (sets Content-Type: application/json)
- `--timeout N` -- Request timeout in seconds (default: 30)

## Output

- Success: status code + response body (auto-formatted if JSON)
- Failure: error message + response body if available
