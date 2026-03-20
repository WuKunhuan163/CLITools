---
name: go-backend
description: Go backend development patterns and idioms. Use when working with go backend concepts or setting up related projects.
---

# Go Backend Development

## Core Principles

- **Accept Interfaces, Return Structs**: Callers define interfaces they need
- **Error Values**: Return errors explicitly; don't panic for expected failures
- **Context Propagation**: Pass `context.Context` as the first parameter
- **Goroutine Lifecycle**: Always ensure goroutines terminate (use context or done channels)

## Key Patterns

### HTTP Handler
```go
func handleGetUser(db *sql.DB) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        id := r.PathValue("id")
        user, err := findUser(r.Context(), db, id)
        if err != nil {
            http.Error(w, "not found", http.StatusNotFound)
            return
        }
        json.NewEncoder(w).Encode(user)
    }
}
```

### Middleware Pattern
```go
func logging(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        next.ServeHTTP(w, r)
        log.Printf("%s %s %v", r.Method, r.URL.Path, time.Since(start))
    })
}
```

### Graceful Shutdown
```go
srv := &http.Server{Addr: ":8080", Handler: mux}
go srv.ListenAndServe()
<-quit
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()
srv.Shutdown(ctx)
```

## Anti-Patterns
- Goroutine leaks (always provide cancellation)
- Empty error handling (`if err != nil { }`)
- Using `init()` for complex initialization
