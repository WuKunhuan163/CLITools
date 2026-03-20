---
name: test-driven-development
description: TDD methodology and red-green-refactor cycle. Use when working with test driven development concepts or setting up related projects.
---

# Test-Driven Development (TDD)

## Core Cycle: Red-Green-Refactor

1. **Red**: Write a failing test for the next small behavior
2. **Green**: Write the minimum code to make it pass
3. **Refactor**: Clean up code while keeping tests green

## Example Walkthrough

### Step 1: Red
```python
def test_fizzbuzz_returns_fizz_for_multiples_of_3():
    assert fizzbuzz(3) == "Fizz"
    assert fizzbuzz(6) == "Fizz"
# Fails: fizzbuzz not defined
```

### Step 2: Green
```python
def fizzbuzz(n):
    if n % 3 == 0: return "Fizz"
    return str(n)
```

### Step 3: Refactor
Clean up while tests stay green. Then write the next failing test.

## Principles

- **Small Steps**: Each test adds one small requirement
- **YAGNI**: Don't write code you don't have a test for
- **Triangulation**: Add more test cases to drive out general solutions
- **Test List**: Maintain a list of behaviors to test before starting

## When TDD Works Best
- Well-defined business logic
- Algorithm development
- API contract design
- Bug reproduction (write failing test first, then fix)

## When to Skip TDD
- Exploratory/prototype code
- UI layout (test interactions instead)
- Configuration/glue code
