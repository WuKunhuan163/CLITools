---
name: cpp-modern
description: Modern C++ (C++17/20/23) best practices. Use when working with cpp modern concepts or setting up related projects.
---

# Modern C++ Best Practices

## Key Features

### Smart Pointers (no raw `new`/`delete`)
```cpp
auto ptr = std::make_unique<Widget>(42);    // exclusive ownership
auto shared = std::make_shared<Widget>(42); // shared ownership
```

### Range-Based For
```cpp
std::vector<int> nums = {1, 2, 3, 4, 5};
for (const auto& n : nums) { std::cout << n; }
```

### Structured Bindings (C++17)
```cpp
auto [name, age] = std::make_pair("Alice", 30);
for (const auto& [key, value] : my_map) { ... }
```

### std::optional (C++17)
```cpp
std::optional<int> find_user(const std::string& name) {
    if (auto it = users.find(name); it != users.end())
        return it->second;
    return std::nullopt;
}
```

### Concepts (C++20)
```cpp
template<typename T>
concept Numeric = std::integral<T> || std::floating_point<T>;

template<Numeric T>
T add(T a, T b) { return a + b; }
```

## RAII (Resource Acquisition Is Initialization)
- Acquire resources in constructors, release in destructors
- Use smart pointers, `std::lock_guard`, `std::fstream`
- Never call `new`/`delete` directly

## Anti-Patterns
- Raw pointers for ownership (use smart pointers)
- Manual memory management (use RAII)
- `using namespace std;` in headers
- Not using `const` where applicable
