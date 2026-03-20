---
name: swiftui-patterns
description: SwiftUI declarative UI patterns. Use when working with swiftui patterns concepts or setting up related projects.
---

# SwiftUI Patterns

## Core Principles

- **Declarative**: Describe what the UI looks like, not how to build it
- **State-Driven**: UI is a function of state; mutations trigger re-renders
- **Composition**: Build views from small, reusable components
- **Property Wrappers**: `@State`, `@Binding`, `@ObservedObject`, `@EnvironmentObject`

## State Management

### @State (local, value type)
```swift
@State private var count = 0
```

### @Binding (parent-child)
```swift
struct ChildView: View {
    @Binding var isOn: Bool
}
```

### @ObservedObject (reference type)
```swift
class UserModel: ObservableObject {
    @Published var name = ""
}
```

## Key Patterns
```swift
struct ContentView: View {
    @StateObject private var viewModel = ContentViewModel()
    var body: some View {
        List(viewModel.items) { item in
            NavigationLink(destination: DetailView(item: item)) {
                Text(item.title)
            }
        }
        .task { await viewModel.loadItems() }
    }
}
```

## Anti-Patterns
- Using `@ObservedObject` when `@StateObject` is needed (object recreated on re-render)
- Massive body properties (extract subviews)
- Force unwrapping optionals in views
