---
name: concurrency-patterns
description: Concurrency and parallelism patterns. Use when working with concurrency patterns concepts or setting up related projects.
---

# Concurrency Patterns

## Core Concepts

- **Concurrency**: Managing multiple tasks (may not run simultaneously)
- **Parallelism**: Actually executing multiple tasks simultaneously
- **Thread Safety**: Shared mutable state requires synchronization
- **Async I/O**: Non-blocking I/O for I/O-bound workloads

## Python Patterns

### asyncio (I/O-bound)
```python
async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in urls]
        return await asyncio.gather(*tasks)
```

### ThreadPoolExecutor (I/O-bound, blocking libraries)
```python
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=10) as pool:
    results = list(pool.map(download_file, urls))
```

### ProcessPoolExecutor (CPU-bound)
```python
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor() as pool:
    results = list(pool.map(compute_heavy, data_chunks))
```

## Synchronization Primitives
- **Lock/Mutex**: Exclusive access to shared resource
- **Semaphore**: Limit concurrent access (e.g., connection pool)
- **Queue**: Thread-safe producer/consumer communication
- **Event**: Signal between threads/coroutines

## Anti-Patterns
- Sharing mutable state without locks
- Using threads for CPU-bound Python (GIL; use processes)
- Creating too many threads (use thread pools)
- Not handling task cancellation and timeouts
