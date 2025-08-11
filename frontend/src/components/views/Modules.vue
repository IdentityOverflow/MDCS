<script setup lang="ts">
import { ref } from 'vue'
import NewModule from './NewModule.vue'
import ModuleCard from '../ModuleCard.vue'

interface Module {
  id: string
  name: string
  description: string
  content: string
  type: 'simple' | 'advanced'
  trigger_pattern?: string
  script?: string
  timing?: 'before' | 'after' | 'custom'
}

const showNewModule = ref(false)

// Dummy modules for testing
const modules = ref<Module[]>([
  {
    id: 'module_1',
    name: 'Data Validator',
    description: 'Validates incoming data structures and ensures data integrity before processing.',
    content: 'Advanced validation logic here...',
    type: 'advanced',
    trigger_pattern: '/validate/*',
    timing: 'before'
  },
  {
    id: 'module_2',
    name: 'Logger',
    description: 'Simple logging utility for tracking system events and debugging information.',
    content: 'console.log implementation...',
    type: 'simple'
  },
  {
    id: 'module_3',
    name: 'Authentication Handler',
    description: 'Manages user authentication and session validation with advanced security features.',
    content: 'JWT token validation and user session management...',
    type: 'advanced',
    trigger_pattern: '/auth/*',
    timing: 'before'
  },
  {
    id: 'module_4',
    name: 'Cache Manager',
    description: 'Handles data caching to improve performance and reduce database load.',
    content: 'Redis cache implementation...',
    type: 'simple'
  },
  {
    id: 'module_5',
    name: 'Error Handler',
    description: 'Global error handling system with custom error reporting and recovery mechanisms.',
    content: 'try-catch wrapper with custom error types...',
    type: 'advanced',
    trigger_pattern: 'error.*',
    timing: 'after'
  },
  {
    id: 'module_6',
    name: 'Notification Service',
    description: 'Sends notifications to users via email, SMS, and push notifications.',
    content: 'Multi-channel notification system...',
    type: 'simple'
  },
  {
    id: 'module_7',
    name: 'Rate Limiter',
    description: 'Controls API request rates to prevent abuse and ensure fair usage across all users.',
    content: 'Token bucket algorithm implementation...',
    type: 'advanced',
    trigger_pattern: '/api/*',
    timing: 'before'
  },
  {
    id: 'module_8',
    name: 'File Processor',
    description: 'Processes uploaded files and converts them to various formats.',
    content: 'File upload and conversion logic...',
    type: 'simple'
  }
])

function createNewModule() {
  showNewModule.value = true
}

function goBackToModules() {
  showNewModule.value = false
}

function editModule(id: string) {
  console.log('Edit module:', id)
}

function deleteModule(id: string) {
  console.log('Delete module:', id)
}
</script>

<template>
  <div class="view-container">
    <NewModule v-if="showNewModule" @back="goBackToModules" />
    <div v-else class="modules-content">
      <div class="header">
        <h1>Modules</h1>
        <button class="action-btn new-btn" @click="createNewModule">
          <i class="fa-solid fa-plus"></i>
          New
        </button>
      </div>
      <div class="content-area">
        <div class="modules-grid">
          <ModuleCard
            v-for="module in modules"
            :key="module.id"
            :module="module"
            @edit="editModule"
            @delete="deleteModule"
          />
        </div>
      </div>
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

</style>