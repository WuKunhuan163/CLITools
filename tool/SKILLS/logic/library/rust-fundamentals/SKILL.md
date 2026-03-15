---
name: rust-fundamentals
description: Rust ownership, borrowing, and idiomatic patterns. Use when working with rust fundamentals concepts or setting up related projects.
---

# Rust Fundamentals

## Core Concepts

### Ownership Rules
1. Each value has exactly one owner
2. When the owner goes out of scope, the value is dropped
3. Ownership can be transferred (moved) or borrowed

### Borrowing
```rust
fn print_length(s: &str) {  // immutable borrow
    println!("Length: {}", s.len());
}

fn push_char(s: &mut String) {  // mutable borrow
    s.push('!');
}
```

### Pattern Matching
```rust
enum Shape {
    Circle(f64),
    Rectangle(f64, f64),
}

fn area(shape: &Shape) -> f64 {
    match shape {
        Shape::Circle(r) => std::f64::consts::PI * r * r,
        Shape::Rectangle(w, h) => w * h,
    }
}
```

### Error Handling with Result
```rust
fn read_config(path: &str) -> Result<Config, Box<dyn Error>> {
    let content = fs::read_to_string(path)?;  // ? propagates error
    let config: Config = serde_json::from_str(&content)?;
    Ok(config)
}
```

### Traits (Interfaces)
```rust
trait Summary {
    fn summarize(&self) -> String;
}
impl Summary for Article {
    fn summarize(&self) -> String { format!("{}: {}", self.title, self.author) }
}
```

## Anti-Patterns
- Fighting the borrow checker with `clone()` everywhere
- Using `unwrap()` in production code (use `?` or proper error handling)
- Overly complex lifetime annotations (simplify data structures)
