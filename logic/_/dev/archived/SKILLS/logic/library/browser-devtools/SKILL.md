---
name: browser-devtools
description: Browser DevTools techniques for debugging and profiling. Use when working with browser devtools concepts or setting up related projects.
---

# Browser DevTools Mastery

## Core Techniques

### Console
- `console.table(data)` for tabular display
- `console.group()` / `console.groupEnd()` for organized output
- `console.time('label')` / `console.timeEnd('label')` for timing
- `$0` references the currently selected DOM element in Elements panel

### Network Panel
- Filter by XHR, Fetch, WS, or custom patterns
- Throttle to simulate slow connections (3G, offline)
- Block specific requests to test error handling

### Performance Panel
- Record user interactions; identify long tasks (>50ms)
- Look for layout thrashing (forced synchronous layouts)
- Check Main thread flame chart for bottlenecks

### Memory Panel
- Take heap snapshots to find memory leaks
- Compare snapshots before/after suspected leak actions
- Track detached DOM nodes

## Debugging Tips
- `debugger;` statement pauses execution in Sources panel
- Conditional breakpoints: right-click line number in Sources
- `monitor(fn)` logs every call to a function
- `getEventListeners($0)` shows all listeners on selected element
