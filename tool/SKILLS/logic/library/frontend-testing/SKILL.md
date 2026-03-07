---
name: frontend-testing
description: Frontend component and integration testing strategies. Use when working with frontend testing concepts or setting up related projects.
---

# Frontend Testing

## Core Principles

- **Testing Library Philosophy**: Test behavior, not implementation details
- **User-Centric Queries**: Use `getByRole`, `getByLabelText` over `getByTestId`
- **Integration Over Unit**: Test component compositions, not isolated internals
- **Mock Minimally**: Only mock network requests and external services

## Key Patterns

### React Testing Library
```tsx
import { render, screen, fireEvent } from '@testing-library/react';

test('submits form with user input', async () => {
  render(<LoginForm onSubmit={mockSubmit} />);
  await userEvent.type(screen.getByLabelText('Email'), 'a@b.com');
  await userEvent.click(screen.getByRole('button', { name: /submit/i }));
  expect(mockSubmit).toHaveBeenCalledWith({ email: 'a@b.com' });
});
```

### MSW for API Mocking
```ts
import { http, HttpResponse } from 'msw';
export const handlers = [
  http.get('/api/user', () => HttpResponse.json({ name: 'John' })),
];
```

## Testing Pyramid (Frontend)
1. **Static Analysis**: TypeScript + ESLint (cheapest, broadest)
2. **Unit Tests**: Pure functions, hooks, utilities
3. **Integration Tests**: Component interactions with mocked APIs
4. **E2E Tests**: Critical user flows with Playwright/Cypress
