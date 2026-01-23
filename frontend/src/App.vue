<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'

// Initialize default connection settings on app startup
onMounted(() => {
  // Initialize Ollama defaults if not already configured
  if (!localStorage.getItem('ollama-connection')) {
    const defaultOllamaConnection = {
      host: 'http://host.docker.internal:11434',
      route: '/api/chat',
      default_model: '',
      keep_alive: '5m',
      format: null,
      options: {
        temperature: 0.8,
        top_p: 0.9,
        top_k: 40,
        min_p: 0.0,
        num_predict: 128,
        num_ctx: 2048,
        seed: 0,
        repeat_penalty: 1.1,
        repeat_last_n: 64,
        tfs_z: 1.0,
        mirostat: 0,
        mirostat_tau: 5.0,
        mirostat_eta: 0.1,
        stop: []
      }
    }
    localStorage.setItem('ollama-connection', JSON.stringify(defaultOllamaConnection))
  }

  // Note: OpenAI connection requires user configuration (API key), so no defaults are set
})
</script>

<template>
  <div id="app">
    <RouterView />
  </div>
</template>

<style>
/* Import global markdown styles (must be non-scoped to work with v-html) */
@import './assets/markdown.css';

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