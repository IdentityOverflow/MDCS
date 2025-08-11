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

/* Custom scrollbar styling */
* {
  scrollbar-width: thin;
  scrollbar-color: var(--border) var(--bg);
}

/* Webkit browsers (Chrome, Safari, Edge) */
*::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

*::-webkit-scrollbar-track {
  background: var(--bg);
  border: 1px solid var(--surface);
}

*::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, var(--border) 0%, var(--secondary) 100%);
  border: 1px solid var(--border);
  transition: background 0.3s ease;
}

*::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(135deg, var(--fg) 0%, var(--border) 100%);
  box-shadow: 0 0 5px var(--glow);
}

*::-webkit-scrollbar-corner {
  background: var(--bg);
}
</style>