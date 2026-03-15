---
name: nextjs-app-router
description: Next.js App Router patterns and best practices. Use when working with nextjs app router concepts or setting up related projects.
---

# Next.js App Router

## Core Principles

- **Server Components by Default**: Components are Server Components unless marked with `'use client'`
- **Streaming**: Use `loading.tsx` and `Suspense` for progressive rendering
- **Route Groups**: Use `(groupName)` folders to organize without affecting URL
- **Parallel Routes**: Use `@slot` for simultaneous route rendering

## Key Patterns

### Server Component Data Fetching
```tsx
// app/posts/page.tsx (Server Component - no 'use client')
async function PostsPage() {
  const posts = await db.post.findMany();
  return <PostList posts={posts} />;
}
```

### Server Actions for Mutations
```tsx
'use server'
async function createPost(formData: FormData) {
  await db.post.create({ data: { title: formData.get('title') } });
  revalidatePath('/posts');
}
```

### Route Segment Config
```tsx
export const dynamic = 'force-dynamic'; // or 'force-static'
export const revalidate = 3600; // ISR: revalidate every hour
```

## Anti-Patterns
- Marking entire pages as `'use client'` when only a small interactive part needs it
- Fetching data on the client when it could be done on the server
- Not using `revalidatePath` / `revalidateTag` after mutations
