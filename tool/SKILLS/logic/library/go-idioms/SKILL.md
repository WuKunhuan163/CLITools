---
name: go-idioms
description: Go idiomatic patterns and best practices. Use when working with go idioms concepts or setting up related projects.
---

# Go Idioms

## Core Principles

- **Simplicity**: The Go way is the simple way
- **Explicit Over Implicit**: No magic; errors returned, not thrown
- **Composition Over Inheritance**: Embed structs, implement interfaces implicitly
- **Small Interfaces**: Prefer one-method interfaces

## Key Patterns

### Error Handling
```go
func readConfig(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("readConfig: %w", err)
    }
    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        return nil, fmt.Errorf("readConfig: parse: %w", err)
    }
    return &cfg, nil
}
```

### Interface Composition
```go
type Reader interface { Read(p []byte) (n int, err error) }
type Writer interface { Write(p []byte) (n int, err error) }
type ReadWriter interface {
    Reader
    Writer
}
```

### Struct Embedding
```go
type Logger struct{ prefix string }
func (l Logger) Log(msg string) { fmt.Println(l.prefix, msg) }

type Server struct {
    Logger
    addr string
}
// server.Log("started") works via embedding
```

### Table-Driven Tests
```go
tests := []struct {
    name  string
    input int
    want  int
}{
    {"positive", 5, 25},
    {"zero", 0, 0},
    {"negative", -3, 9},
}
for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        got := square(tt.input)
        if got != tt.want { t.Errorf("got %d, want %d", got, tt.want) }
    })
}
```

## Anti-Patterns
- Returning interfaces (return concrete types)
- Overusing goroutines without lifecycle management
- Package-level mutable state
