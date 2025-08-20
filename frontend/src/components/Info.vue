<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Persona } from '@/types'
import { getPersonaImage, handleImageError, countComponents } from '@/composables/utils'

const props = defineProps<{
  selectedPersona: Persona | null
}>()

const secondaryScreenText = ref('STATUS OK')
const showImage = ref(false)
const secondaryMessages = ['ALERT', 'SCAN', 'READY', 'LINK']
let secondaryIndex = 0

const displayText = computed(() => {
  if (props.selectedPersona) {
    const componentCount = countComponents(props.selectedPersona.template)
    let text = `NAME: ${props.selectedPersona.name}\n`
    text += `MODE: ${props.selectedPersona.mode.toUpperCase()}\n`
    if (props.selectedPersona.mode === 'autonomous' && props.selectedPersona.loop_frequency) {
      text += `FREQ: ${props.selectedPersona.loop_frequency}HZ\n`
    }
    text += `COMPONENTS: ${componentCount}\n\n`
    text += `DESCRIPTION:\n${props.selectedPersona.description}`
    return text
  }
  return secondaryScreenText.value
})


function toggleView() {
  showImage.value = !showImage.value
}


onMounted(() => {
  setInterval(() => {
    if (!props.selectedPersona) {
      secondaryIndex = (secondaryIndex + 1) % secondaryMessages.length
      secondaryScreenText.value = secondaryMessages[secondaryIndex]
    }
  }, 4000)
})
</script>

<template>
  <div class="info-combined">
    <div class="screen-secondary">
      <div class="grid-overlay"></div>
      <div class="scan-line"></div>
      
      <!-- Toggle button (only visible when persona is selected) -->
      <button 
        v-if="selectedPersona" 
        class="toggle-btn" 
        @click="toggleView"
        :title="showImage ? 'Show Info' : 'Show Image'"
      >
        <i :class="showImage ? 'fa-solid fa-info' : 'fa-solid fa-image'"></i>
      </button>
      
      <!-- Content display -->
      <div v-if="!selectedPersona || !showImage" class="screen-secondary-content" :class="{ 'multi-line': selectedPersona }">
        {{ displayText }}
      </div>
      
      <!-- Image display -->
      <div v-else class="image-display">
        <img :src="getPersonaImage(selectedPersona.image_path)" :alt="selectedPersona.name" @error="handleImageError" />
      </div>
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

.toggle-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  background: rgba(0, 255, 65, 0.2);
  border: 1px solid #00ff41;
  color: #00ff41;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  transition: all 0.2s ease;
  z-index: 10;
}

.toggle-btn:hover {
  background: rgba(0, 255, 65, 0.3);
  box-shadow: 0 0 8px rgba(0, 255, 65, 0.5);
}

.image-display {
  position: absolute;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  box-sizing: border-box;
}

.image-display img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  filter: drop-shadow(0 0 10px rgba(0, 255, 65, 0.4));
  border: 1px solid rgba(0, 255, 65, 0.3);
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
  padding: 8px;
  box-sizing: border-box;
}

.screen-secondary-content.multi-line {
  font-size: 10px;
  line-height: 1.4;
  white-space: pre-line;
  text-align: left;
  align-items: flex-start;
  padding-top: 12px;
  overflow-y: auto;
  justify-content: flex-start;
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