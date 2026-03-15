---
name: android-jetpack-compose
description: Android Jetpack Compose patterns. Use when working with android jetpack compose concepts or setting up related projects.
---

# Android Jetpack Compose

## Core Principles

- **Composable Functions**: UI elements are functions annotated with `@Composable`
- **Unidirectional Data Flow**: State flows down, events flow up
- **Remember**: Use `remember` and `rememberSaveable` to preserve state across recompositions
- **Side Effects**: Use `LaunchedEffect`, `DisposableEffect` for lifecycle-aware operations

## Key Patterns

### State Hoisting
```kotlin
@Composable
fun Counter(count: Int, onIncrement: () -> Unit) {
    Button(onClick = onIncrement) { Text("Count: $count") }
}

@Composable
fun CounterScreen() {
    var count by remember { mutableStateOf(0) }
    Counter(count = count, onIncrement = { count++ })
}
```

### ViewModel Integration
```kotlin
@Composable
fun UserScreen(viewModel: UserViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    when (uiState) {
        is Loading -> CircularProgressIndicator()
        is Success -> UserList(uiState.users)
        is Error -> ErrorMessage(uiState.message)
    }
}
```

## Anti-Patterns
- Performing side effects directly in composable functions
- Not using `key` in `LazyColumn` items
- Heavy computation inside composition (use `remember` or ViewModel)
