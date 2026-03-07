---
name: logging-best-practices
description: Application logging patterns and structured logging. Use when working with logging best practices concepts or setting up related projects.
---

# Logging Best Practices

## Core Principles

- **Structured Logging**: JSON format for machine parsing
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL (use appropriately)
- **Correlation IDs**: Trace requests across services
- **No Sensitive Data**: Never log passwords, tokens, PII

## Python Structured Logging
```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "correlation_id": getattr(record, 'correlation_id', None),
        })
```

## What to Log

### Always Log
- Request start/end with duration
- Authentication events (login, logout, failure)
- Business-critical operations (order placed, payment processed)
- Errors with stack traces

### Never Log
- Passwords, API keys, tokens
- Full credit card numbers
- Personal health information
- Session IDs in URL parameters

## Log Levels Guide
- **DEBUG**: Detailed diagnostic info (development only)
- **INFO**: Normal operation events (request handled, job completed)
- **WARNING**: Unexpected but handled situations (retry, fallback used)
- **ERROR**: Operation failed but application continues
- **CRITICAL**: Application cannot continue

## Anti-Patterns
- Using `print()` instead of logging framework
- Logging at wrong level (everything as INFO)
- No structured format (grep-unfriendly)
- Logging inside tight loops (performance impact)
