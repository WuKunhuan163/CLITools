---
name: nodejs-patterns
description: Node.js backend patterns and best practices. Use when working with nodejs patterns concepts or setting up related projects.
---

# Node.js Patterns

## Core Principles

- **Non-Blocking I/O**: Use async/await; never block the event loop
- **Error Handling**: Always handle promise rejections and stream errors
- **Structured Logging**: Use `pino` or `winston` with JSON format
- **Graceful Shutdown**: Handle `SIGTERM`/`SIGINT` for clean process exit

## Key Patterns

### Express Error Handling
```js
app.use((err, req, res, next) => {
  const status = err.statusCode || 500;
  res.status(status).json({
    error: { message: err.message, code: err.code || 'INTERNAL_ERROR' }
  });
});
```

### Graceful Shutdown
```js
process.on('SIGTERM', async () => {
  server.close();
  await db.disconnect();
  process.exit(0);
});
```

### Stream Processing
```js
const transform = new Transform({
  transform(chunk, encoding, callback) {
    callback(null, chunk.toString().toUpperCase());
  }
});
readStream.pipe(transform).pipe(writeStream);
```

## Anti-Patterns
- Synchronous file operations in request handlers
- Unhandled promise rejections (always `.catch()` or try/catch)
- Using `console.log` in production (use structured logger)
