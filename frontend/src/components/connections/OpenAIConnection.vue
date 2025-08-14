<script setup lang="ts">
import { onMounted } from 'vue'
import { useLocalStorage, useNotification } from '@/composables/storage'

// Default OpenAI connection settings
const defaultOpenAIConnection = {
  base_url: 'https://api.openai.com/v1',
  api_key: '',
  organization: '',
  project: '',
  api_type: 'openai',
  api_version: '',
  deployment: '',
  default_model: '',
  compatibility_mode: 'responses',
  stream: true,
  timeout_ms: 60000,
  extra_headers: {}
}

// Storage management
const { data: openaiConnection, save: saveToStorage, load: loadFromStorage } = useLocalStorage({
  key: 'openai-connection',
  defaultValue: defaultOpenAIConnection,
  validate: (value) => {
    return value && typeof value.base_url === 'string' && typeof value.api_key === 'string'
  }
})

// Notification system
const notification = useNotification()

// Load data on component mount
onMounted(() => {
  loadFromStorage()
})

function saveConnection() {
  if (!openaiConnection.value.api_key.trim()) {
    notification.showError('API Key is required')
    return
  }
  
  if (!openaiConnection.value.default_model.trim()) {
    notification.showError('Default Model is required')
    return
  }

  const success = saveToStorage()
  if (success) {
    notification.showSuccess('OpenAI connection saved successfully')
  } else {
    notification.showError('Failed to save connection')
  }
}

function testConnection() {
  console.log('Testing OpenAI connection...', openaiConnection.value)
  // TODO: Implement actual connection test
  notification.showSuccess('Connection test feature coming soon')
}
</script>

<template>
  <form class="form" @submit.prevent="saveConnection">
      <div class="form-group">
        <label for="openai-base-url">Base URL</label>
        <input 
          id="openai-base-url"
          v-model="openaiConnection.base_url" 
          type="text" 
          class="form-input"
          placeholder="https://api.openai.com/v1"
        />
        <small class="form-hint">Root API URL. For Azure/OpenAI-compatible vendors, set their base endpoint</small>
      </div>

      <div class="form-group">
        <label for="openai-api-key">API Key *</label>
        <input 
          id="openai-api-key"
          v-model="openaiConnection.api_key" 
          type="password" 
          class="form-input"
          placeholder="sk-..."
          required
        />
        <small class="form-hint">Bearer token used for Authorization header</small>
      </div>

      <div class="form-group">
        <label for="openai-model">Default Model *</label>
        <input 
          id="openai-model"
          v-model="openaiConnection.default_model" 
          type="text" 
          class="form-input"
          placeholder="gpt-4o"
          required
        />
        <small class="form-hint">Model ID (e.g., gpt-4.1, gpt-4o, etc.) or Azure deployment name</small>
      </div>

      <div class="form-group">
        <label for="openai-organization">Organization</label>
        <input 
          id="openai-organization"
          v-model="openaiConnection.organization" 
          type="text" 
          class="form-input"
          placeholder="org-..."
        />
        <small class="form-hint">Optional OpenAI org header (OpenAI-Organization)</small>
      </div>

      <div class="form-group">
        <label for="openai-project">Project</label>
        <input 
          id="openai-project"
          v-model="openaiConnection.project" 
          type="text" 
          class="form-input"
          placeholder="proj_..."
        />
        <small class="form-hint">Optional OpenAI project header (OpenAI-Project)</small>
      </div>

      <div class="form-group">
        <label for="openai-api-type">API Type</label>
        <select id="openai-api-type" v-model="openaiConnection.api_type" class="form-select">
          <option value="openai">OpenAI</option>
          <option value="other">Other</option>
        </select>
        <small class="form-hint">Needed to shape paths/headers</small>
      </div>

      <div class="form-group">
        <label for="openai-compatibility-mode">Compatibility Mode</label>
        <select id="openai-compatibility-mode" v-model="openaiConnection.compatibility_mode" class="form-select">
          <option value="responses">Responses API</option>
          <option value="chat_completions">Chat Completions</option>
        </select>
        <small class="form-hint">Prefer Responses API for new builds; fall back to Chat Completions when required</small>
      </div>

      <div class="form-group">
        <label for="openai-timeout">Timeout (ms)</label>
        <input 
          id="openai-timeout"
          v-model.number="openaiConnection.timeout_ms" 
          type="number" 
          class="form-input"
          min="1000"
          max="300000"
        />
        <small class="form-hint">Client request timeout</small>
      </div>

      <div class="form-group">
        <label class="form-checkbox-label">
          <input 
            v-model="openaiConnection.stream" 
            type="checkbox" 
            class="form-checkbox"
          />
          <span class="form-checkbox-custom"></span>
          Enable SSE streaming
        </label>
      </div>

      <div class="form-actions">
        <button type="button" @click="testConnection" class="action-btn cancel-btn">
          <i class="fa-solid fa-plug"></i>
          Test Connection
        </button>
        <button type="submit" class="action-btn save-btn">
          <i class="fa-solid fa-save"></i>
          Save Configuration
        </button>
      </div>
  </form>
  
  <!-- Notification Toast -->
  <div v-if="notification.isVisible.value" class="notification-toast" :class="notification.type.value">
    <i :class="notification.type.value === 'success' ? 'fa-solid fa-check' : 'fa-solid fa-exclamation-triangle'"></i>
    {{ notification.message.value }}
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';
@import '@/assets/form.css';

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