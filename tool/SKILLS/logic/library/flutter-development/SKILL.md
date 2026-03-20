---
name: flutter-development
description: Flutter development patterns and state management. Use when working with flutter development concepts or setting up related projects.
---

# Flutter Development

## Core Principles

- **Widget Composition**: Build complex UIs from small, focused widgets
- **Immutable State**: Rebuild widgets when state changes (don't mutate)
- **Keys**: Use keys for list items and stateful widgets that move
- **Null Safety**: Embrace Dart's sound null safety

## State Management Options

### Provider (simple)
```dart
class Counter extends ChangeNotifier {
  int _count = 0;
  int get count => _count;
  void increment() { _count++; notifyListeners(); }
}
```

### Riverpod (recommended)
```dart
final counterProvider = StateNotifierProvider<CounterNotifier, int>(
  (ref) => CounterNotifier(),
);
```

### BLoC (enterprise)
Separate business logic from UI with events and states.

## Performance Tips
- Use `const` constructors wherever possible
- Minimize widget rebuilds with `Selector`/`Consumer`
- Use `ListView.builder` instead of `ListView` for long lists
- Profile with Flutter DevTools

## Anti-Patterns
- Single giant widget instead of composition
- `setState` in deeply nested widgets (use proper state management)
- Not disposing controllers and streams
