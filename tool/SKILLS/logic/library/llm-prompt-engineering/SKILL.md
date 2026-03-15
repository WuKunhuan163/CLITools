---
name: llm-prompt-engineering
description: LLM prompt engineering techniques and patterns. Use when working with llm prompt engineering concepts or setting up related projects.
---

# LLM Prompt Engineering

## Core Principles

- **Be Specific**: Detailed instructions produce better results than vague ones
- **Few-Shot Examples**: Show the model examples of desired input/output
- **System Prompts**: Set role, constraints, and output format
- **Chain of Thought**: Ask the model to reason step-by-step

## Techniques

### Few-Shot Prompting
```
Classify the sentiment: "This product is amazing!" -> Positive
Classify the sentiment: "Terrible experience." -> Negative
Classify the sentiment: "It was okay, nothing special." -> Neutral
Classify the sentiment: "I love this new feature!" ->
```

### Chain of Thought
```
Q: If a store sells 3 apples for $2, how much do 15 apples cost?
A: Let me think step by step.
1. 3 apples cost $2
2. Price per apple: $2 / 3 = $0.667
3. 15 apples: 15 * $0.667 = $10
```

### Structured Output
```
Extract entities from the text and return JSON:
{"persons": [...], "locations": [...], "dates": [...]}
```

### Role-Based System Prompt
```
You are a senior Python developer who follows PEP 8 strictly.
When asked to write code, include type hints and docstrings.
Always consider edge cases and error handling.
```

## Anti-Patterns
- Ambiguous instructions ("make it better")
- Overly long prompts that dilute the key instruction
- Not validating structured output from the model
