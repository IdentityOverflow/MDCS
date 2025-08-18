<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useModules } from '@/composables/useModules'
import { useNotification } from '@/composables/storage'
import NewModule from './NewModule.vue'
import ModuleCard from '../ModuleCard.vue'

const showNewModule = ref(false)
const editingModule = ref<string | null>(null)

// Use the modules composable for API integration
const {
  modules,
  loading,
  error,
  fetchModules,
  deleteModule: deleteModuleAPI,
  clearError
} = useModules()

// Notification system
const notification = useNotification()

// Load modules on component mount
onMounted(async () => {
  await loadModules()
})

async function loadModules() {
  await fetchModules()
  
  if (error.value) {
    notification.showError(`Failed to load modules: ${error.value}`)
  }
}

function createNewModule() {
  showNewModule.value = true
  editingModule.value = null
}

function goBackToModules() {
  showNewModule.value = false
  editingModule.value = null
  // Refresh modules list in case something was created/updated
  loadModules()
}

function editModule(id: string) {
  editingModule.value = id
  showNewModule.value = true
}

async function handleDeleteModule(id: string) {
  if (!confirm('Are you sure you want to delete this module?')) {
    return
  }
  
  const success = await deleteModuleAPI(id)
  
  if (success) {
    notification.showSuccess('Module deleted successfully!')
  } else if (error.value) {
    notification.showError(`Failed to delete module: ${error.value}`)
    clearError()
  }
}
</script>

<template>
  <div class="view-container">
    <NewModule 
      v-if="showNewModule" 
      :editing-module-id="editingModule"
      @back="goBackToModules" 
    />
    <div v-else class="modules-content">
      <div class="header">
        <h1>Modules</h1>
        <button 
          class="action-btn new-btn" 
          @click="createNewModule"
          :disabled="loading"
        >
          <i class="fa-solid fa-plus"></i>
          New
        </button>
      </div>
      <div class="content-area">
        <!-- Loading state -->
        <div v-if="loading" class="loading-container">
          <div class="loading-text">
            <i class="fa-solid fa-spinner fa-spin"></i>
            Loading modules...
          </div>
        </div>
        
        <!-- Error state -->
        <div v-else-if="error" class="error-container">
          <div class="error-text">
            <i class="fa-solid fa-exclamation-triangle"></i>
            {{ error }}
          </div>
          <button class="action-btn retry-btn" @click="loadModules">
            <i class="fa-solid fa-refresh"></i>
            Retry
          </button>
        </div>
        
        <!-- Empty state -->
        <div v-else-if="modules.length === 0" class="empty-container">
          <div class="empty-text">
            <i class="fa-solid fa-puzzle-piece"></i>
            <h3>No modules found</h3>
            <p>Create your first module to get started</p>
          </div>
          <button class="action-btn create-btn" @click="createNewModule">
            <i class="fa-solid fa-plus"></i>
            Create Module
          </button>
        </div>
        
        <!-- Modules grid -->
        <div v-else class="modules-grid">
          <ModuleCard
            v-for="module in modules"
            :key="module.id"
            :module="module"
            @edit="editModule"
            @delete="handleDeleteModule"
          />
        </div>
      </div>
    </div>
    
    <!-- Notification Toast -->
    <div v-if="notification.isVisible.value" class="notification-toast" :class="notification.type.value">
      <i :class="notification.type.value === 'success' ? 'fa-solid fa-check' : 'fa-solid fa-exclamation-triangle'"></i>
      {{ notification.message.value }}
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';

.view-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.modules-content {
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

.modules-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 0 4px;
}

/* Loading state */
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.loading-text {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--fg);
  font-size: 1.1em;
  opacity: 0.8;
}

.loading-text i {
  color: var(--accent);
  font-size: 1.2em;
}

/* Error state */
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  min-height: 200px;
  justify-content: center;
}

.error-text {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #ef4444;
  font-size: 1.1em;
  text-align: center;
}

.error-text i {
  font-size: 1.2em;
}

.retry-btn {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid #ef4444;
  color: #ef4444;
}

.retry-btn:hover {
  background: rgba(239, 68, 68, 0.2);
}

/* Empty state */
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  min-height: 300px;
  justify-content: center;
}

.empty-text {
  text-align: center;
  color: var(--fg);
  opacity: 0.7;
}

.empty-text i {
  font-size: 3em;
  color: var(--accent);
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-text h3 {
  font-size: 1.4em;
  margin: 0 0 8px 0;
  font-weight: 600;
}

.empty-text p {
  margin: 0;
  opacity: 0.8;
}

.create-btn {
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid var(--accent);
  color: var(--accent);
}

.create-btn:hover {
  background: rgba(0, 212, 255, 0.2);
}

/* Notification toast */
.notification-toast {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 12px 16px;
  border-radius: 4px;
  color: white;
  font-weight: 600;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 250px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  animation: slideIn 0.3s ease;
}

.notification-toast.success {
  background: linear-gradient(135deg, #10b981, #059669);
  border: 1px solid #047857;
}

.notification-toast.error {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  border: 1px solid #b91c1c;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

</style>