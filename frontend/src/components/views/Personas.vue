<script setup lang="ts">
import { ref, computed } from 'vue'
import NewPersona from './NewPersona.vue'

const showNewPersona = ref(false)
const currentIndex = ref(4) // Start at center (index 4 of 9 items)

// Mock data for 9 personas
const personas = ref([
  { id: 1, name: 'Persona 1', image: '/src/assets/persona.png' },
  { id: 2, name: 'Persona 2', image: '/src/assets/persona.png' },
  { id: 3, name: 'Persona 3', image: '/src/assets/persona.png' },
  { id: 4, name: 'Persona 4', image: '/src/assets/persona.png' },
  { id: 5, name: 'Persona 5', image: '/src/assets/persona.png' },
  { id: 6, name: 'Persona 6', image: '/src/assets/persona.png' },
  { id: 7, name: 'Persona 7', image: '/src/assets/persona.png' },
  { id: 8, name: 'Persona 8', image: '/src/assets/persona.png' },
  { id: 9, name: 'Persona 9', image: '/src/assets/persona.png' }
])

const getItemTransform = (index: number) => {
  let distance = index - currentIndex.value
  
  // Handle wrapping for circular effect
  if (distance > personas.value.length / 2) {
    distance -= personas.value.length
  } else if (distance < -personas.value.length / 2) {
    distance += personas.value.length
  }
  
  const absDistance = Math.abs(distance)
  
  // Center item is much bigger (2.5x) for text legibility, others scale down more dramatically
  const scale = absDistance === 0 ? 2.5 : Math.max(0.3, 1 - absDistance * 0.3)
  const translateX = distance * 180
  const translateZ = absDistance === 0 ? 100 : -absDistance * 50
  
  return {
    transform: `translateX(${translateX}px) translateZ(${translateZ}px) scale(${scale})`,
    opacity: absDistance > 2 ? 0 : Math.max(0.15, 1 - absDistance * 0.35)
  }
}

function createNewPersona() {
  showNewPersona.value = true
}

function goBackToPersonas() {
  showNewPersona.value = false
}

function previousPersona() {
  currentIndex.value = currentIndex.value === 0 ? personas.value.length - 1 : currentIndex.value - 1
}

function nextPersona() {
  currentIndex.value = currentIndex.value === personas.value.length - 1 ? 0 : currentIndex.value + 1
}
</script>

<template>
  <div class="view-container">
    <NewPersona v-if="showNewPersona" @back="goBackToPersonas" />
    <div v-else class="personas-content">
      <h1>Personas</h1>
      <div class="content-area">
        <div class="carousel-container">
          <div class="carousel-3d">
            <div 
              v-for="(persona, index) in personas" 
              :key="persona.id"
              class="carousel-item"
              :class="{ active: index === currentIndex }"
              :style="getItemTransform(index)"
            >
              <div class="persona-card">
                <img :src="persona.image" :alt="persona.name" />
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="controls-section">
        <div class="carousel-controls">
          <button 
            class="nav-btn" 
            @click="previousPersona"
          >
            &lt;
          </button>
          <button 
            class="nav-btn" 
            @click="nextPersona"
          >
            &gt;
          </button>
        </div>
        
        <div class="action-buttons">
          <button class="action-btn new-btn" @click="createNewPersona">
            <i class="fa-solid fa-plus"></i>
            New
          </button>
          <button class="action-btn delete-btn">
            <i class="fa-solid fa-trash"></i>
            Delete
          </button>
          <button class="action-btn edit-btn">
            <i class="fa-solid fa-edit"></i>
            Edit
          </button>
          <button class="action-btn connect-btn">
            <i class="fa-solid fa-link"></i>
            Connect
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.view-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.personas-content {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

h1 {
  color: var(--fg);
  font-size: 1.6em;
  font-weight: 600;
  margin-bottom: 16px;
  text-align: center;
}

.content-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--fg);
  perspective: 1200px;
  overflow: hidden;
}

.carousel-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.carousel-3d {
  position: relative;
  width: 100%;
  height: 200px;
  transform-style: preserve-3d;
  display: flex;
  align-items: center;
  justify-content: center;
}

.carousel-item {
  position: absolute;
  width: 120px;
  height: 160px;
  transition: all 0.8s cubic-bezier(0.23, 1, 0.32, 1);
  transform-origin: center center;
  will-change: transform, opacity;
}

.carousel-item.active {
  z-index: 10;
}

.persona-card {
  width: 100%;
  height: 100%;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.persona-card img {
  width: 120px;
  height: 160px;
  object-fit: contain;
  transition: all 0.3s ease;
}

.controls-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
}

.carousel-controls {
  display: flex;
  gap: 20px;
  align-items: center;
}

.nav-btn {
  background: linear-gradient(135deg, var(--bg) 0%, var(--secondary) 100%);
  border: 1px solid var(--border);
  color: var(--fg);
  border-radius: 50%;
  width: 40px;
  height: 40px;
  cursor: pointer;
  font-size: 1.2em;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  box-shadow: inset 0 0 10px var(--glow);
}

.nav-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--secondary) 0%, var(--surface) 100%);
  border-color: var(--fg);
  box-shadow: 0 0 10px var(--glow);
  transform: translateY(-2px);
}

.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.action-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: center;
}

.action-btn {
  border: 1px solid var(--border);
  color: var(--fg);
  border-radius: 0;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 0.9em;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.3s ease;
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%);
  position: relative;
}

.action-btn::before {
  content: '';
  position: absolute;
  bottom: 6px;
  right: 0;
  width: 11px;
  height: 1px;
  transform: rotate(-45deg);
  transform-origin: right center;
}

.new-btn {
  background: linear-gradient(135deg, var(--bg) 0%, var(--secondary) 100%);
  border-color: var(--border);
  border-left: 5px solid var(--accent);
  box-shadow: inset 0 0 10px var(--glow);
}

.new-btn::before {
  background: var(--border);
}

.new-btn:hover {
  background: linear-gradient(135deg, var(--secondary) 0%, var(--surface) 100%);
  border-color: var(--fg);
  box-shadow: 0 0 10px var(--glow);
  transform: translateY(-2px);
}

.delete-btn {
  background: linear-gradient(135deg, var(--bg) 0%, var(--secondary) 100%);
  border-color: var(--border);
  border-left: 5px solid #dc143c;
  box-shadow: inset 0 0 10px var(--glow);
}

.delete-btn::before {
  background: var(--border);
}

.delete-btn:hover {
  background: linear-gradient(135deg, var(--secondary) 0%, var(--surface) 100%);
  border-color: var(--fg);
  box-shadow: 0 0 10px var(--glow);
  transform: translateY(-2px);
}

.edit-btn {
  background: linear-gradient(135deg, var(--bg) 0%, var(--secondary) 100%);
  border-color: var(--border);
  border-left: 5px solid #00ffff;
  box-shadow: inset 0 0 10px var(--glow);
}

.edit-btn::before {
  background: var(--border);
}

.edit-btn:hover {
  background: linear-gradient(135deg, var(--secondary) 0%, var(--surface) 100%);
  border-color: var(--fg);
  box-shadow: 0 0 10px var(--glow);
  transform: translateY(-2px);
}

.connect-btn {
  background: linear-gradient(135deg, var(--bg) 0%, var(--secondary) 100%);
  border-color: var(--border);
  border-left: 5px solid #2196f3;
  box-shadow: inset 0 0 10px var(--glow);
}

.connect-btn::before {
  background: var(--border);
}

.connect-btn:hover {
  background: linear-gradient(135deg, var(--secondary) 0%, var(--surface) 100%);
  border-color: var(--fg);
  box-shadow: 0 0 10px var(--glow);
  transform: translateY(-2px);
}

.action-btn i {
  font-size: 1em;
}

</style>