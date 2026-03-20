---
name: e2e-testing
description: End-to-end testing with Playwright. Use when working with e2e testing concepts or setting up related projects.
---

# E2E Testing with Playwright

## Core Principles

- **Test User Flows**: Focus on critical paths (signup, checkout, core features)
- **Isolation**: Each test should be independent; use fresh state
- **Auto-Waiting**: Playwright auto-waits for elements; avoid explicit sleeps
- **Page Object Model**: Abstract page interactions into reusable classes

## Key Patterns

### Basic Test
```ts
import { test, expect } from '@playwright/test';

test('user can log in', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('user@example.com');
  await page.getByLabel('Password').fill('password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByText('Welcome')).toBeVisible();
});
```

### Page Object Model
```ts
class LoginPage {
  constructor(private page: Page) {}
  async login(email: string, password: string) {
    await this.page.getByLabel('Email').fill(email);
    await this.page.getByLabel('Password').fill(password);
    await this.page.getByRole('button', { name: 'Sign in' }).click();
  }
}
```

### API Mocking
```ts
await page.route('**/api/users', route =>
  route.fulfill({ json: [{ id: 1, name: 'Alice' }] })
);
```

## Anti-Patterns
- Testing everything with E2E (use unit/integration tests for logic)
- Fragile selectors (use roles and labels, not CSS classes)
- Tests that depend on previous test state
