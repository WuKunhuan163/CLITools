---
name: python-fastapi
description: Python FastAPI development patterns. Use when working with python fastapi concepts or setting up related projects.
---

# Python FastAPI

## Core Principles

- **Type Hints**: FastAPI uses Pydantic models and type annotations for validation
- **Async by Default**: Use `async def` endpoints for I/O-bound operations
- **Dependency Injection**: Use `Depends()` for shared logic (auth, DB sessions)
- **Auto Documentation**: OpenAPI/Swagger docs generated from type annotations

## Key Patterns

### Pydantic Model
```python
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    name: str
    email: EmailStr

class UserResponse(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)
```

### Dependency Injection
```python
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    return db.query(User).get(user_id)
```

### Background Tasks
```python
@app.post("/send-email")
async def send(background_tasks: BackgroundTasks):
    background_tasks.add_task(send_email, "user@example.com")
    return {"status": "queued"}
```

## Anti-Patterns
- Blocking I/O in async endpoints (use `run_in_executor` or sync def)
- Not using response models (leaks internal fields)
- Putting all routes in one file (use `APIRouter`)
