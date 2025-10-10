import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Split vendor libraries into separate chunks
          'codemirror': ['codemirror', '@codemirror/lang-python', '@codemirror/theme-one-dark'],
          'markdown': ['marked'],
          'vue-vendor': ['vue', 'vue-router', 'pinia']
        }
      }
    },
    // Increase warning limit to 600 KB (optional, but helps avoid warnings for reasonable sizes)
    chunkSizeWarningLimit: 600
  }
})
