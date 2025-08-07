<script setup lang="ts">
import { ref, onMounted } from 'vue'

const secondaryScreenText = ref('STATUS OK')
const secondaryMessages = ['ALERT', 'SCAN', 'READY', 'LINK']
let secondaryIndex = 0

onMounted(() => {
  setInterval(() => {
    secondaryIndex = (secondaryIndex + 1) % secondaryMessages.length
    secondaryScreenText.value = secondaryMessages[secondaryIndex]
  }, 4000)
})
</script>

<template>
  <div class="info-combined">
    <div class="screen-secondary">
      <div class="grid-overlay"></div>
      <div class="scan-line"></div>
      <div class="screen-secondary-content">{{ secondaryScreenText }}</div>
    </div>
  </div>
</template>

<style scoped>
.info-combined {
  background: var(--surface);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 2px;
  font-weight: bold;
  text-transform: uppercase;
  font-size: 1.2em;
  grid-area: F;
}

.screen-secondary {
  position: relative;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #0a1628 0%, #1e3a5f 50%, #0a1628 100%);
  overflow: hidden;
  box-shadow: 
      0 0 30px rgba(0, 255, 65, 0.4),
      inset 0 0 20px rgba(0, 255, 65, 0.1);
}

.screen-secondary .scan-line {
  position: absolute;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #00ff41, transparent);
  animation: scan 2s linear infinite;
}

.screen-secondary .grid-overlay {
  position: absolute;
  width: 100%;
  height: 100%;
  background-image: 
      repeating-linear-gradient(0deg, transparent, transparent 8px, rgba(0, 255, 65, 0.05) 8px, rgba(0, 255, 65, 0.05) 9px),
      repeating-linear-gradient(90deg, transparent, transparent 8px, rgba(0, 255, 65, 0.05) 8px, rgba(0, 255, 65, 0.05) 9px);
  pointer-events: none;
}

.screen-secondary-content {
  position: absolute;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #00ff41;
  text-shadow: 0 0 10px rgba(0, 255, 65, 0.8);
  animation: flicker 3s infinite;
}

@keyframes scan {
  0% { top: 0%; }
  100% { top: 100%; }
}

@keyframes flicker {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.85; }
}
</style>