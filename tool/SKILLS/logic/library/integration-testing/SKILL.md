---
name: integration-testing
description: Integration testing patterns for APIs and databases. Use when working with integration testing concepts or setting up related projects.
---

# Integration Testing

## Core Principles

- **Test Real Interactions**: Use actual database, message queue, or service
- **Isolated Environment**: Docker Compose or testcontainers for dependencies
- **Transaction Rollback**: Wrap tests in transactions for automatic cleanup
- **Seed Minimal Data**: Only create what the specific test needs

## Patterns

### Testcontainers (Python)
```python
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def db():
    with PostgresContainer("postgres:16") as postgres:
        engine = create_engine(postgres.get_connection_url())
        Base.metadata.create_all(engine)
        yield engine
```

### Transaction Rollback
```python
@pytest.fixture
def session(db):
    connection = db.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    transaction.rollback()
    connection.close()
```

### API Integration Test
```python
def test_create_and_retrieve_user(client, db_session):
    resp = client.post("/users", json={"name": "Alice"})
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    resp = client.get(f"/users/{user_id}")
    assert resp.json()["name"] == "Alice"
```

## Anti-Patterns
- Shared mutable test data between tests
- Tests that depend on execution order
- Not cleaning up test data (use transactions or truncation)
