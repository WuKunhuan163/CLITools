---
name: java-spring-boot
description: Java Spring Boot development patterns. Use when working with java spring boot concepts or setting up related projects.
---

# Java Spring Boot

## Core Principles

- **Convention Over Configuration**: Spring Boot auto-configures sensible defaults
- **Dependency Injection**: Use constructor injection (preferred over field injection)
- **Layered Architecture**: Controller -> Service -> Repository
- **Profiles**: Use `application-{profile}.yml` for environment-specific config

## Key Patterns

### REST Controller
```java
@RestController
@RequestMapping("/api/v1/users")
public class UserController {
    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserDTO> getUser(@PathVariable Long id) {
        return ResponseEntity.ok(userService.findById(id));
    }
}
```

### Exception Handler
```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(NotFoundException ex) {
        return ResponseEntity.status(404).body(new ErrorResponse(ex.getMessage()));
    }
}
```

## Anti-Patterns
- Field injection with `@Autowired` (use constructor injection)
- Business logic in controllers
- Not using DTOs (exposing entities directly)
