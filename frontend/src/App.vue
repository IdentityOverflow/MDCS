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

  /* Theme colors */
  --bg: #1e1e1e;
  --fg: #e0e0e0;
  --surface: #2e2e2e;
  --border: #3c3c3c;
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