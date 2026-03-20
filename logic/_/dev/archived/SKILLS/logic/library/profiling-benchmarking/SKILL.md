---
name: profiling-benchmarking
description: Code profiling and benchmarking techniques. Use when working with profiling benchmarking concepts or setting up related projects.
---

# Profiling & Benchmarking

## Python Profiling

### cProfile
```python
import cProfile
cProfile.run('my_function()', sort='cumulative')

# Or as decorator
import functools
def profile(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        result = profiler.runcall(func, *args, **kwargs)
        profiler.print_stats(sort='cumulative')
        return result
    return wrapper
```

### Line Profiler
```python
@profile
def compute():
    total = sum(range(1000000))  # shows time per line
    return total
```

### Memory Profiling
```python
from memory_profiler import profile
@profile
def create_data():
    data = [i ** 2 for i in range(1000000)]
    return data
```

## JavaScript Profiling
- Chrome DevTools Performance panel
- `console.time()` / `console.timeEnd()` for quick timing
- `performance.mark()` and `performance.measure()` for precise timing

## Benchmarking Rules
1. **Warm up**: Run function several times before measuring
2. **Multiple iterations**: Average over many runs
3. **Isolate**: Benchmark one thing at a time
4. **Real data**: Use production-like data sizes
5. **Statistics**: Report median and percentiles, not just mean

## Anti-Patterns
- Optimizing without profiling first
- Micro-benchmarks that don't reflect real usage
- Benchmarking with `time.time()` for sub-millisecond operations (use `perf_counter`)
