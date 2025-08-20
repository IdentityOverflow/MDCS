<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import NewPersona from './NewPersona.vue'
import PersonaCard from '../PersonaCard.vue'
import { usePersonas } from '@/composables/usePersonas'
import type { Persona } from '@/types'

const showNewPersona = ref(false)
const editingPersonaId = ref<string | null>(null)
const selectedPersonaId = ref<string | null>(null)

const emit = defineEmits<{
  selectPersona: [persona: Persona]
}>()

// Use personas composable
const {
  personas,
  loading,
  error,
  fetchPersonas,
  deletePersona: deletePersonaAPI,
  clearError
} = usePersonas()

// Computed values for UI state
const hasPersonas = computed(() => personas.value.length > 0)
const showEmpty = computed(() => !loading.value && !hasPersonas.value && !error.value)
const showError = computed(() => !loading.value && error.value)

// Lifecycle
onMounted(async () => {
  try {
    await fetchPersonas()
    // Load selected persona ID from localStorage
    selectedPersonaId.value = localStorage.getItem('selectedPersonaId')
  } catch (err) {
    console.error('Failed to load personas:', err)
  }
})

// Event handlers
function createNewPersona() {
  editingPersonaId.value = null
  showNewPersona.value = true
}

function goBackToPersonas() {
  showNewPersona.value = false
  editingPersonaId.value = null
  // Refresh personas when returning from form
  fetchPersonas()
}

function handlePersonaSelect(persona: Persona) {
  // Update local state
  selectedPersonaId.value = persona.id
  // Update localStorage (this will also be done by HomeView, but doing it here too for consistency)
  localStorage.setItem('selectedPersonaId', persona.id)
  // Emit to parent
  emit('selectPersona', persona)
}

function editPersona(id: string) {
  editingPersonaId.value = id
  showNewPersona.value = true
}

async function handleDeletePersona(id: string) {
  if (!confirm('Are you sure you want to delete this persona?')) {
    return
  }
  
  try {
    await deletePersonaAPI(id)
    console.log('Persona deleted successfully')
  } catch (err) {
    console.error('Failed to delete persona:', err)
    alert('Failed to delete persona. Please try again.')
  }
}

function handleErrorDismiss() {
  clearError()
}
</script>

<template>
  <div class="view-container">
    <NewPersona 
      v-if="showNewPersona" 
      :editing-persona-id="editingPersonaId"
      @back="goBackToPersonas" 
    />
    <div v-else class="personas-content">
      <div class="header">
        <h1>Personas</h1>
        <button class="action-btn new-btn" @click="createNewPersona" :disabled="loading">
          <i class="fa-solid fa-plus"></i>
          New
        </button>
      </div>
      <div class="content-area">
        <!-- Loading State -->
        <div v-if="loading" class="loading-state">
          <i class="fa-solid fa-spinner fa-spin"></i>
          <p>Loading personas...</p>
        </div>
        
        <!-- Error State -->
        <div v-else-if="showError" class="error-state">
          <i class="fa-solid fa-exclamation-triangle"></i>
          <p>{{ error }}</p>
          <button class="action-btn retry-btn" @click="fetchPersonas">
            <i class="fa-solid fa-redo"></i>
            Retry
          </button>
          <button class="action-btn dismiss-btn" @click="handleErrorDismiss">
            Dismiss
          </button>
        </div>
        
        <!-- Empty State -->
        <div v-else-if="showEmpty" class="empty-container">
          <div class="empty-text">
            <i class="fa-solid fa-user-plus"></i>
            <h3>No personas found</h3>
            <p>Create your first AI persona to get started</p>
          </div>
          <button class="action-btn create-btn" @click="createNewPersona">
            <i class="fa-solid fa-plus"></i>
            Create Persona
          </button>
        </div>
        
        <!-- Personas Grid -->
        <div v-else class="personas-grid">
          <PersonaCard
            v-for="persona in personas"
            :key="persona.id"
            :persona="persona"
            :selected="selectedPersonaId === persona.id"
            @select="handlePersonaSelect"
            @edit="editPersona"
            @delete="handleDeletePersona"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';
@import '@/assets/empty-states.css';

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

.header {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 16px;
  position: relative;
}

h1 {
  color: var(--fg);
  font-size: 1.6em;
  font-weight: 600;
  margin: 0;
}

.new-btn {
  position: absolute;
  right: 0;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.personas-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 0 4px;
}

/* State styles */
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  text-align: center;
  color: var(--fg-muted);
}

.loading-state i {
  font-size: 2em;
  margin-bottom: 16px;
  color: var(--accent);
}

.error-state i {
  font-size: 2em;
  margin-bottom: 16px;
  color: var(--error);
}

.error-state p {
  margin: 8px 0;
  font-size: 1.1em;
}

.error-state .action-btn {
  margin: 4px 8px;
}

</style>