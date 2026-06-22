<template>
  <view class="app-root">
    <slot />
  </view>
</template>

<style>
page {
  min-height: 100%;
  background: var(--color-bg);
  color: var(--color-text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.app-root {
  min-height: 100vh;
  background: var(--color-bg);
}
</style>

