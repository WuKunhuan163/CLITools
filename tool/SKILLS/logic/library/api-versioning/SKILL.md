---
name: api-versioning
description: API versioning strategies and migration patterns. Use when working with api versioning concepts or setting up related projects.
---

# API Versioning

## Strategies

### URL Path Versioning
```
GET /api/v1/users
GET /api/v2/users
```
Pros: Explicit, easy to route. Cons: URL pollution.

### Header Versioning
```
GET /api/users
Accept: application/vnd.myapp.v2+json
```
Pros: Clean URLs. Cons: Harder to test in browser.

### Query Parameter
```
GET /api/users?version=2
```
Pros: Simple. Cons: Easy to forget.

## Migration Patterns

### Expand and Contract
1. **Expand**: Add new fields/endpoints alongside old ones
2. **Migrate**: Update clients to use new format
3. **Contract**: Remove deprecated fields/endpoints

### Deprecation Process
```
Sunset: Sat, 01 Mar 2027 00:00:00 GMT
Deprecation: true
Link: <https://api.example.com/docs/migration>; rel="deprecation"
```

### Backward Compatible Changes (No version bump needed)
- Adding new optional fields to responses
- Adding new endpoints
- Adding optional query parameters

### Breaking Changes (Require version bump)
- Removing fields from responses
- Changing field types
- Changing URL structure
- Changing authentication scheme

## Best Practices
- Support at least N-1 versions
- Communicate deprecation timeline clearly (6+ months)
- Provide migration guides for breaking changes
- Use feature flags for gradual rollout
