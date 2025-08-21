<script setup lang="ts">
import { ref, onMounted } from 'vue'
import MainChat from '../components/MainChat.vue'
import DisplayArea from '../components/DisplayArea.vue'
import ControlPanel from '../components/ControlPanel.vue'
import Info from '../components/Info.vue'
import { useChat } from '@/composables/useChat'
import { usePersonas } from '@/composables/usePersonas'
import type { Persona } from '@/types'

const selectedComponent = ref('Personas')
const selectedPersona = ref<Persona | null>(null)

// Use chat composable for conversation loading
const { loadConversationForPersona, currentConversation, isLoadingConversation } = useChat()
const { getPersonaById } = usePersonas()

// Load selected persona from localStorage on mount
onMounted(async () => {
  const savedPersonaId = localStorage.getItem('selectedPersonaId')
  if (savedPersonaId) {
    // Load the persona details and its conversation
    const persona = getPersonaById(savedPersonaId)
    if (persona) {
      selectedPersona.value = persona
      // Load conversation for this persona
      try {
        await loadConversationForPersona(savedPersonaId)
        console.log('Loaded conversation for persona:', persona.name)
      } catch (error) {
        console.error('Failed to load conversation for persona:', error)
      }
    } else {
      console.log('Saved persona ID not found, will fetch from API:', savedPersonaId)
    }
  }
})

function handleComponentSelect(componentName: string) {
  selectedComponent.value = componentName
}

async function handlePersonaSelect(persona: Persona) {
  selectedPersona.value = persona
  // Save selected persona ID to localStorage for persistence
  localStorage.setItem('selectedPersonaId', persona.id)
  console.log('Selected persona:', persona.name)
  
  // Load conversation for the selected persona
  try {
    await loadConversationForPersona(persona.id)
    console.log('Loaded conversation for selected persona:', persona.name)
  } catch (error) {
    console.error('Failed to load conversation for selected persona:', error)
  }
}
</script>

<template>
  <div class="container">
    <MainChat />
    <DisplayArea :selected-component="selectedComponent" @select-persona="handlePersonaSelect" />
    <ControlPanel @select-component="handleComponentSelect" />
    <Info 
      :selected-persona="selectedPersona" 
      :current-conversation="currentConversation" 
      :is-loading-conversation="isLoadingConversation" 
    />
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
