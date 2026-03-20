# Blueprint Extensibility Guide

Blueprints support external backends, multi-language executors, and complex trigger conditions.

## External Backends (Other Languages)

A backend doesn't have to be Python. Any process that speaks JSON over stdin/stdout can serve as a brain backend.

### Executor Config

Add an `executor` section to your blueprint to declare a non-Python backend:

```json
{
  "name": "my-rust-brain-20260316",
  "version": "1.0",
  "inherits": "base",
  "tiers": {
    "knowledge": {
      "backend": "external",
      "relative_path": "knowledge/",
      "executor": {
        "type": "process",
        "command": ["./bin/brain-server", "--tier", "knowledge"],
        "protocol": "jsonrpc",
        "working_directory": "{instance_root}",
        "env": {
          "BRAIN_TIER": "knowledge",
          "BRAIN_DATA_DIR": "{tier_path}"
        }
      },
      "files": {}
    }
  }
}
```

### Executor Types

| Type | Description | Protocol |
|------|-------------|----------|
| `process` | Spawn a subprocess per operation | stdin/stdout JSON or JSON-RPC |
| `http` | Call an HTTP endpoint | REST API (POST with JSON body) |
| `grpc` | Call a gRPC service | Protocol Buffers |
| `socket` | Unix domain socket | JSON-RPC over socket |
| `module` | Python module (default) | Direct function calls |

### Process Executor Protocol

The process receives JSON on stdin and writes JSON to stdout:

**Request:**
```json
{
  "method": "store",
  "params": {
    "tier": "knowledge",
    "key": "lessons",
    "value": {"lesson": "...", "tool": "LLM"}
  }
}
```

**Response:**
```json
{
  "result": {"status": "ok"},
  "error": null
}
```

Supported methods: `store`, `retrieve`, `search`, `append`, `list_keys`.

### HTTP Executor

```json
{
  "executor": {
    "type": "http",
    "base_url": "http://localhost:8420/brain",
    "headers": {"Authorization": "Bearer {env:BRAIN_TOKEN}"},
    "timeout_ms": 5000,
    "health_check": "/health"
  }
}
```

### Template Variables

Executors support template variables resolved at runtime:

| Variable | Description |
|----------|-------------|
| `{instance_root}` | Absolute path to the brain instance directory |
| `{tier_path}` | Absolute path to the tier's data directory |
| `{session_name}` | Name of the current brain session |
| `{project_root}` | Absolute path to the project root |
| `{env:VAR_NAME}` | Environment variable value |

## Complex Trigger Conditions

### Basic Triggers

Triggers define when brain data gets injected or processed:

```json
{
  "context_injection": {
    "sessionStart": {
      "sources": [
        {
          "type": "brain_state",
          "tier": "working",
          "files": ["context", "tasks"],
          "format": "markdown"
        }
      ]
    }
  }
}
```

### Conditional Triggers

Triggers can have conditions evaluated at runtime:

```json
{
  "triggers": {
    "auto_summarize": {
      "event": "postToolUse",
      "condition": {
        "type": "threshold",
        "metric": "working.activity.line_count",
        "operator": ">",
        "value": 100
      },
      "action": {
        "type": "execute",
        "command": "BRAIN digest --auto"
      }
    },
    "knowledge_sync": {
      "event": "timer",
      "interval_minutes": 30,
      "action": {
        "type": "execute",
        "command": "BRAIN session manifest"
      }
    },
    "lesson_threshold": {
      "event": "postAppend",
      "condition": {
        "type": "count",
        "tier": "knowledge",
        "key": "lessons",
        "operator": "modulo",
        "value": 10,
        "remainder": 0
      },
      "action": {
        "type": "notify",
        "message": "10 new lessons accumulated. Consider: BRAIN digest"
      }
    }
  }
}
```

### Condition Types

| Type | Description | Parameters |
|------|-------------|------------|
| `threshold` | Numeric comparison | `metric`, `operator` (>, <, ==, >=, <=), `value` |
| `count` | Count-based | `tier`, `key`, `operator`, `value`, `remainder` |
| `file_exists` | File existence check | `path` (template variables supported) |
| `time_elapsed` | Time since last event | `event`, `minutes` |
| `expression` | Python expression | `expr` (evaluated in sandbox) |

### Action Types

| Type | Description | Parameters |
|------|-------------|------------|
| `execute` | Run a CLI command | `command` |
| `notify` | Show a notification to the agent | `message` |
| `inject` | Inject data into agent context | `sources` |
| `webhook` | Call an external URL | `url`, `method`, `body` |

## Multi-Language Example: Node.js Brain Backend

```json
{
  "name": "node-vector-20260316",
  "version": "1.0",
  "inherits": "base",
  "description": "Vector brain using Node.js with LanceDB for semantic search.",
  "tiers": {
    "knowledge": {
      "backend": "external",
      "relative_path": "knowledge/",
      "executor": {
        "type": "process",
        "command": ["node", "logic/brain/backends/node-vector/server.js"],
        "protocol": "jsonrpc",
        "working_directory": "{project_root}",
        "env": {
          "BRAIN_DATA_DIR": "{tier_path}"
        },
        "lifecycle": "daemon",
        "startup_timeout_ms": 3000
      },
      "files": {
        "index": "lance_db/",
        "metadata": "metadata.json"
      }
    }
  },
  "dependencies": {
    "npm": ["lancedb", "@lancedb/vectordb"],
    "note": "Run: cd logic/brain/backends/node-vector && npm install"
  }
}
```

## Interface Extensions

Blueprints can declare custom interface methods beyond the standard `store/retrieve/search/append/list_keys`:

```json
{
  "interface_extensions": {
    "summarize": {
      "description": "Generate a summary of tier contents",
      "params": {"tier": "string", "max_tokens": "int"},
      "returns": "string"
    },
    "cluster_lessons": {
      "description": "Cluster lessons by topic using embeddings",
      "params": {"min_cluster_size": "int"},
      "returns": "array"
    }
  }
}
```

These are exposed through the standard brain interface and dispatched to the backend's executor.
