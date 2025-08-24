<script setup lang="ts">
import { ref, computed } from 'vue'
import ExpandedModal from './ExpandedModal.vue'
import Personas from './views/Personas.vue'
import Modules from './views/Modules.vue'
import Scratchpad from './views/Scratchpad.vue'
import Tools from './views/Tools.vue'
import Files from './views/Files.vue'
import Settings from './views/Settings.vue'
import Rooms from './views/Rooms.vue'
import Debug from './views/Debug.vue'
import Scripting from './views/Scripting.vue'

const props = defineProps<{
  selectedComponent: string
}>()

const emit = defineEmits<{
  selectPersona: [persona: any]
  selectComponent: [componentName: string]
}>()

// Modal state
const isExpanded = ref(false)

const currentComponent = computed(() => {
  switch (props.selectedComponent) {
    case 'Personas': return Personas
    case 'Modules': return Modules
    case 'Scratchpad': return Scratchpad
    case 'Tools': return Tools
    case 'Files': return Files
    case 'Settings': return Settings
    case 'Rooms': return Rooms
    case 'Debug': return Debug
    case 'Scripting': return Scripting
    default: return Personas
  }
})

// Modal actions
const expandView = () => {
  isExpanded.value = true
}

const closeModal = () => {
  isExpanded.value = false
}
</script>

<template>
  <div class="display-area">
    <!-- Expand button -->
    <button 
      class="expand-btn card-icon-btn"
      @click="expandView"
      title="Expand to full view"
    >
      <i class="fa-solid fa-expand"></i>
    </button>
    
    <!-- Normal view content -->
    <div class="display-content">
      <component :is="currentComponent" @select-persona="emit('selectPersona', $event)" />
    </div>
  </div>

  <!-- Expanded Modal -->
  <ExpandedModal 
    :selected-component="selectedComponent" 
    :is-visible="isExpanded"
    @close="closeModal"
    @select-persona="emit('selectPersona', $event)"
    @select-component="emit('selectComponent', $event)"
  />
</template>

<style scoped>
@import '@/assets/card.css';

.display-area {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 2px;
  grid-area: B;
  position: relative;
}

/* Expand button positioning */
.expand-btn {
  position: absolute;
  bottom: 0;
  left: 0;
  z-index: 10;
  opacity: 0.7;
  transition: opacity 0.2s ease;
  border-radius: 0;
  border-bottom: none;
  border-left: none;
}

.expand-btn:hover {
  opacity: 1;
}

.display-content {
  height: 100%;
  width: 100%;
}
</style>