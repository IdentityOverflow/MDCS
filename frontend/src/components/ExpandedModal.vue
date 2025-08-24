<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import Personas from './views/Personas.vue'
import Modules from './views/Modules.vue'
import Scratchpad from './views/Scratchpad.vue'
import Tools from './views/Tools.vue'
import Files from './views/Files.vue'
import Settings from './views/Settings.vue'
import Rooms from './views/Rooms.vue'
import Debug from './views/Debug.vue'

const props = defineProps<{
  selectedComponent: string
  isVisible: boolean
}>()

const emit = defineEmits<{
  close: []
  selectPersona: [persona: any]
  selectComponent: [componentName: string]
}>()

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
    default: return Personas
  }
})

// Close on escape key
const handleKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && props.isVisible) {
    emit('close')
  }
}

// Lifecycle management
onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<template>
  <!-- Modal overlay -->
  <Teleport to="body">
    <div v-if="isVisible" class="modal-overlay">
      <div class="modal-tablet" @click.stop>
        <!-- Close button -->
        <button 
          class="close-btn card-icon-btn"
          @click="emit('close')"
          title="Close (ESC)"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>
        
        <!-- Modal content layout -->
        <div class="modal-layout">
          <!-- Main content area -->
          <div class="modal-content">
            <component :is="currentComponent" @select-persona="emit('selectPersona', $event)" />
          </div>
          
          <!-- Side panel with navigation buttons -->
          <div class="modal-sidebar">
            <div class="navigation-buttons">
              <button class="cyberpunk-btn tablet-nav" @click="emit('selectComponent', 'Personas')">
                <i class="fa-solid fa-user-tie"></i>
                <span>Personas</span>
              </button>
              <button class="cyberpunk-btn tablet-nav" @click="emit('selectComponent', 'Modules')">
                <i class="fa-solid fa-puzzle-piece"></i>
                <span>Modules</span>
              </button>
              <button class="cyberpunk-btn tablet-nav" @click="emit('selectComponent', 'Scratchpad')">
                <i class="fa-solid fa-code"></i>
                <span>Scratchpad</span>
              </button>
              <button class="cyberpunk-btn tablet-nav" @click="emit('selectComponent', 'Tools')">
                <i class="fa-solid fa-wrench"></i>
                <span>Tools</span>
              </button>
              <button class="cyberpunk-btn tablet-nav" @click="emit('selectComponent', 'Files')">
                <i class="fa-solid fa-folder"></i>
                <span>Files</span>
              </button>
              <button class="cyberpunk-btn tablet-nav" @click="emit('selectComponent', 'Rooms')">
                <i class="fa-solid fa-door-open"></i>
                <span>Rooms</span>
              </button>
              <button class="cyberpunk-btn tablet-nav" @click="emit('selectComponent', 'Settings')">
                <i class="fa-solid fa-gear"></i>
                <span>Settings</span>
              </button>
              <button class="cyberpunk-btn tablet-nav" @click="emit('selectComponent', 'Debug')">
                <i class="fa-solid fa-bug"></i>
                <span>Debug</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
@import '@/assets/card.css';
@import '@/assets/cyberpunk-buttons.css';

/* Modal overlay - cyberpunk backdrop */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  backdrop-filter: blur(8px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  animation: modalFadeIn 0.3s ease-out;
}

@keyframes modalFadeIn {
  from {
    opacity: 0;
    backdrop-filter: blur(0px);
  }
  to {
    opacity: 1;
    backdrop-filter: blur(8px);
  }
}

/* Cyberpunk tablet design */
.modal-tablet {
  width: 95vw;
  max-width: 1600px;
  height: 90vh;
  background: linear-gradient(135deg, var(--bg) 0%, var(--secondary) 100%);
  border: 2px solid var(--border);
  border-left: 6px solid var(--accent);
  border-radius: 12px;
  box-shadow: 
    0 0 40px rgba(0, 212, 255, 0.3),
    inset 0 0 20px rgba(0, 212, 255, 0.1);
  position: relative;
  display: flex;
  flex-direction: column;
  animation: tabletSlideIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  
  /* Tablet bezel effect - equal padding on all sides */
  padding: 16px; /* top, right, bottom, left */
}

@keyframes tabletSlideIn {
  from {
    transform: scale(0.9) translateY(50px);
    opacity: 0;
  }
  to {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}

/* Cyberpunk tablet corners */
.modal-tablet::before {
  content: '';
  position: absolute;
  top: -2px;
  right: -2px;
  width: 40px;
  height: 40px;
  border-right: 2px solid var(--accent);
  border-top: 2px solid var(--accent);
  border-radius: 0 12px 0 0;
  background: 
    linear-gradient(45deg, transparent 40%, var(--accent) 41%, var(--accent) 43%, transparent 44%),
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0, 212, 255, 0.03) 2px,
      rgba(0, 212, 255, 0.03) 4px
    );
}

.modal-tablet::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: -2px;
  width: 40px;
  height: 40px;
  border-left: 2px solid var(--accent);
  border-bottom: 2px solid var(--accent);
  border-radius: 0 0 0 12px;
  background: linear-gradient(-135deg, transparent 40%, var(--accent) 41%, var(--accent) 43%, transparent 44%);
}

/* Close button positioning */
.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 10;
  color: var(--fg);
  transition: all 0.2s ease;
}

.close-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  transform: rotate(90deg);
}

/* Modal layout - side by side */
.modal-layout {
  display: flex;
  gap: 16px;
  height: 100%;
  min-height: 0; /* Important for flex child overflow */
}

/* Main content area */
.modal-content {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow-y: auto;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.3);
  min-height: 0;
}

/* Sidebar */
.modal-sidebar {
  width: 300px;
  display: flex;
  flex-direction: column;
}

.navigation-buttons {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
  padding: 8px;
  height: 100%;
}

/* Tablet navigation button variant */
.cyberpunk-btn.tablet-nav {
  flex-direction: row;
  justify-content: flex-start;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  min-height: 60px;
  width: 100%;
  text-align: left;
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%);
}

.cyberpunk-btn.tablet-nav::before {
  bottom: 8px;
  width: 18px;
}

.cyberpunk-btn.tablet-nav::after {
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%);
}

.cyberpunk-btn.tablet-nav:not(:disabled):hover {
  transform: translateX(4px);
}

.cyberpunk-btn.tablet-nav i {
  font-size: 1.8em;
  min-width: 32px;
  color: var(--accent);
  transition: color 0.3s ease;
}

.cyberpunk-btn.tablet-nav:not(:disabled):hover i {
  color: var(--fg);
}

.cyberpunk-btn.tablet-nav span {
  font-size: 0.95em;
  font-weight: 600;
  flex: 1;
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

/* Custom scrollbar for modal content */
.modal-content::-webkit-scrollbar {
  width: 8px;
}

.modal-content::-webkit-scrollbar-track {
  background: var(--bg);
  border-radius: 4px;
}

.modal-content::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 4px;
  border: 1px solid var(--accent);
}

.modal-content::-webkit-scrollbar-thumb:hover {
  background: var(--accent);
}

/* Add power indicator light */
.close-btn::before {
  content: '';
  position: absolute;
  top: -8px;
  left: -8px;
  width: 6px;
  height: 6px;
  background: var(--accent);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--accent);
  animation: pulse 2s ease-in-out infinite alternate;
}

@keyframes pulse {
  from {
    opacity: 0.4;
    transform: scale(1);
  }
  to {
    opacity: 1;
    transform: scale(1.2);
  }
}

/* Responsive adjustments for smaller screens */
@media (max-width: 1200px) {
  .modal-sidebar {
    width: 260px;
  }
}

@media (max-width: 900px) {
  .modal-layout {
    flex-direction: column;
  }
  
  .modal-sidebar {
    width: 100%;
    max-height: 240px;
    flex-shrink: 0;
  }
  
  .navigation-buttons {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 8px;
    padding: 12px;
    overflow-y: auto;
  }
  
  .cyberpunk-btn.tablet-nav {
    flex: 1;
    min-width: calc(50% - 4px);
    min-height: 50px;
    padding: 12px 16px;
    gap: 12px;
  }
  
  .cyberpunk-btn.tablet-nav i {
    font-size: 1.4em;
    min-width: 24px;
  }
  
  .cyberpunk-btn.tablet-nav span {
    font-size: 0.85em;
  }
}
</style>