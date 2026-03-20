---
name: regex-patterns
description: Regular expression patterns and best practices. Use when working with regex patterns concepts or setting up related projects.
---

# Regular Expressions

## Common Patterns

### Email (simplified)
```regex
[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
```

### URL
```regex
https?://[\w.-]+(?:\.[\w.-]+)+[\w.,@?^=%&:/~+#-]*
```

### Date (YYYY-MM-DD)
```regex
\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])
```

## Python Usage
```python
import re

# Named groups
pattern = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
match = re.search(pattern, text)
if match:
    print(match.group('year'))

# Substitution
clean = re.sub(r'\s+', ' ', messy_text).strip()

# Non-greedy matching
re.findall(r'<.*?>', html)   # matches individual tags
re.findall(r'<.*>', html)    # greedy: matches everything between first < and last >
```

## Performance Tips
- Compile patterns used in loops: `pattern = re.compile(r'...')`
- Use non-capturing groups `(?:...)` when you don't need the match
- Avoid catastrophic backtracking with nested quantifiers
- Use `re.VERBOSE` for readable multi-line patterns

## Anti-Patterns
- Using regex to parse HTML/XML (use a parser)
- Overly complex regex without comments
- Not anchoring patterns (`^...$`) when full-string match is needed
