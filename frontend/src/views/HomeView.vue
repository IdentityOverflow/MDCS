<script setup lang="ts">
import { ref, onMounted } from 'vue'
import MainChat from '../components/MainChat.vue'
import DisplayArea from '../components/DisplayArea.vue'
import ControlPanel from '../components/ControlPanel.vue'
import Info from '../components/Info.vue'
import type { Persona } from '@/types'

const selectedComponent = ref('Personas')
const selectedPersona = ref<Persona | null>(null)

// Load selected persona from localStorage on mount
onMounted(() => {
  const savedPersonaId = localStorage.getItem('selectedPersonaId')
  if (savedPersonaId) {
    // We'll need to fetch the persona details from the API
    // For now, just store the ID - the actual persona will be set when DisplayArea loads
    console.log('Saved persona ID:', savedPersonaId)
  }
})

function handleComponentSelect(componentName: string) {
  selectedComponent.value = componentName
}

function handlePersonaSelect(persona: Persona) {
  selectedPersona.value = persona
  // Save selected persona ID to localStorage for persistence
  localStorage.setItem('selectedPersonaId', persona.id)
  console.log('Selected persona:', persona.name)
}
</script>

<template>
  <div class="container">
    <MainChat />
    <DisplayArea :selected-component="selectedComponent" @select-persona="handlePersonaSelect" />
    <ControlPanel @select-component="handleComponentSelect" />
    <Info :selected-persona="selectedPersona" />
  </div>
</template>

<style scoped>
.container {
  display: grid;
  width: 100%;
  height: 100%;
  grid-template-columns: var(--col1) var(--col2) var(--col3) var(--col4);
  grid-template-rows: var(--col1) var(--col2) var(--col3) var(--col4);
  grid-template-areas:
    "A B B B"
    "A F F C"
    "A F F C"
    "A F F C";
}
</style>
