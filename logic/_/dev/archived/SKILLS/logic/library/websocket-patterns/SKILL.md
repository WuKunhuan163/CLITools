---
name: websocket-patterns
description: WebSocket real-time communication patterns. Use when working with websocket patterns concepts or setting up related projects.
---

# WebSocket Patterns

## Core Principles

- **Bidirectional**: Both client and server can send messages anytime
- **Heartbeat**: Implement ping/pong to detect dead connections
- **Reconnection**: Client should auto-reconnect with exponential backoff
- **Message Protocol**: Define a structured message format (type + payload)

## Message Format
```json
{"type": "chat.message", "payload": {"room": "general", "text": "Hello"}}
{"type": "user.typing", "payload": {"room": "general", "user": "Alice"}}
```

## Server (Python FastAPI)
```python
from fastapi import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            await ws.send_json({"type": "echo", "payload": data})
    except WebSocketDisconnect:
        pass
```

## Client (JavaScript)
```js
function connect() {
  const ws = new WebSocket('wss://api.example.com/ws');
  ws.onmessage = (event) => handleMessage(JSON.parse(event.data));
  ws.onclose = () => setTimeout(connect, 1000 * Math.random() * 3);
}
```

## Scaling
- Use Redis Pub/Sub or Kafka for multi-server message distribution
- Consider Server-Sent Events (SSE) for one-way server-to-client updates
