<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div id="app">
    <RouterView />
  </div>
</template>

<style>
:root {
  /* Golden ratio and grid fractions */
  --phi: 1.618;
  --col1: 61.8%;
  --col2: 9.02%;
  --col3: 5.58%;
  --col4: 23.6%;

  /* Cyberpunk theme colors */
  --bg: #0a0a0a;
  --fg: #00ffff;
  --surface: #1a1a2e;
  --border: #00d4ff;
  --accent: #ff006e;
  --secondary: #16213e;
  --glow: rgba(0, 255, 255, 0.3);
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  width: 100vw;
  height: 100vh;
  background: var(--bg);
  color: var(--fg);
  font-family: sans-serif;
}

#app {
  width: 100%;
  height: 100%;
}
</style>