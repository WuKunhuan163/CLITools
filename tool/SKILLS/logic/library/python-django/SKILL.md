---
name: python-django
description: Django development best practices. Use when working with python django concepts or setting up related projects.
---

# Django Best Practices

## Core Principles

- **Fat Models, Thin Views**: Put business logic in models/managers, not views
- **QuerySet Chains**: Use ORM efficiently; avoid N+1 with `select_related`/`prefetch_related`
- **Class-Based Views**: Use for CRUD; function-based views for simple/custom logic
- **Signals Sparingly**: Prefer explicit method calls over implicit signal handlers

## Key Patterns

### Custom Manager
```python
class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status='published')

class Article(models.Model):
    objects = models.Manager()
    published = PublishedManager()
```

### Avoid N+1
```python
# Bad: N+1 queries
for order in Order.objects.all():
    print(order.customer.name)

# Good: single JOIN
for order in Order.objects.select_related('customer'):
    print(order.customer.name)
```

### Custom Middleware
```python
class TimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        response['X-Elapsed'] = f"{time.time() - start:.3f}s"
        return response
```

## Anti-Patterns
- Raw SQL when the ORM can handle it
- Business logic in templates
- Not using migrations for schema changes
