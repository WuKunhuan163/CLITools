---
name: react-native-development
description: React Native development patterns with Expo. Use when working with react native development concepts or setting up related projects.
---

# React Native Development

## Core Principles

- **Expo First**: Use Expo unless you need native modules not available in Expo
- **Platform Abstraction**: Use `Platform.select()` and `.ios.js`/`.android.js` for platform code
- **Navigation**: Use React Navigation (stack, tab, drawer) as the standard
- **Performance**: Use `FlatList` (not `ScrollView`) for lists, minimize re-renders

## Key Patterns

### FlatList with Optimization
```tsx
<FlatList
  data={items}
  renderItem={({ item }) => <ItemCard item={item} />}
  keyExtractor={item => item.id}
  getItemLayout={(data, index) => ({ length: 80, offset: 80 * index, index })}
  removeClippedSubviews={true}
/>
```

### Platform-Specific Code
```ts
import { Platform } from 'react-native';
const styles = StyleSheet.create({
  shadow: Platform.select({
    ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 2 } },
    android: { elevation: 4 },
  }),
});
```

## Anti-Patterns
- Inline styles on every render (use `StyleSheet.create`)
- Heavy computation on the JS thread (use `react-native-reanimated` for animations)
- Not testing on both platforms regularly
