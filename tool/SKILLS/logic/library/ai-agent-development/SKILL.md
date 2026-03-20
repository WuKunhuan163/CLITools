---
name: ai-agent-development
description: AI agent development patterns with tool use. Use when working with ai agent development concepts or setting up related projects.
---

# AI Agent Development

## Core Architecture

```
User Input -> Agent (LLM) -> Reasoning -> Tool Selection -> Tool Execution -> Response
                ^                                              |
                |______________________________________________|
                              (Loop until done)
```

## Key Patterns

### Tool Definition
```python
tools = [{
    "type": "function",
    "function": {
        "name": "search_database",
        "description": "Search the product database by query",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    }
}]
```

### ReAct Pattern (Reason + Act)
```
Thought: I need to find the user's order history
Action: search_orders(user_id="123")
Observation: Found 3 orders: [...]
Thought: Now I can summarize the order history
Answer: You have 3 recent orders...
```

### Multi-Agent Collaboration
- **Router Agent**: Decides which specialist agent handles the request
- **Specialist Agents**: Domain-specific (code, search, data analysis)
- **Supervisor**: Orchestrates and validates agent outputs

## Best Practices
- Limit tool calls per turn to prevent infinite loops
- Validate tool outputs before passing back to LLM
- Log all agent actions for debugging and auditing
- Use structured output (JSON) for tool responses
- Implement timeout and cost budgets

## Anti-Patterns
- Letting agents make irreversible actions without confirmation
- No guard rails on tool usage (cost, rate, permissions)
- Single monolithic agent instead of specialized agents
