---
name: java-patterns
description: Java modern patterns and best practices. Use when working with java patterns concepts or setting up related projects.
---

# Java Modern Patterns

## Key Modern Features

### Records (Java 16+)
```java
public record User(String name, String email) {}
// Auto-generates constructor, getters, equals, hashCode, toString
```

### Pattern Matching (Java 21+)
```java
String format(Object obj) {
    return switch (obj) {
        case Integer i -> "int: " + i;
        case String s -> "str: " + s;
        case null -> "null";
        default -> "unknown";
    };
}
```

### Sealed Classes
```java
public sealed interface Shape permits Circle, Rectangle {}
public record Circle(double radius) implements Shape {}
public record Rectangle(double width, double height) implements Shape {}
```

### Streams
```java
List<String> names = users.stream()
    .filter(u -> u.isActive())
    .map(User::getName)
    .sorted()
    .toList();
```

### Virtual Threads (Java 21+)
```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    for (var task : tasks) {
        executor.submit(task);
    }
}
```

## Best Practices
- Prefer immutable objects (records, `List.of()`, `Map.of()`)
- Use `Optional` for nullable return values (not for fields/parameters)
- Prefer composition over inheritance
- Use `var` for local variables when type is obvious

## Anti-Patterns
- Checked exceptions for control flow
- Mutable singletons
- Excessive inheritance hierarchies
