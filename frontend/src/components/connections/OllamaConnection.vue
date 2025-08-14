<script setup lang="ts">
import { onMounted } from 'vue'
import { useLocalStorage, useNotification } from '@/composables/storage'

// Default Ollama connection settings
const defaultOllamaConnection = {
  host: 'http://localhost:11434',
  route: '/api/chat',
  model: '',
  stream: true,
  keep_alive: '5m',
  format: null,
  options: {
    temperature: 0.8,
    top_p: 0.9,
    top_k: 40,
    min_p: 0.0,
    num_predict: 128,
    num_ctx: 2048,
    seed: 0,
    repeat_penalty: 1.1,
    repeat_last_n: 64,
    tfs_z: 1.0,
    mirostat: 0,
    mirostat_tau: 5.0,
    mirostat_eta: 0.1,
    stop: []
  }
}

// Storage management
const { data: ollamaConnection, save: saveToStorage, load: loadFromStorage } = useLocalStorage({
  key: 'ollama-connection',
  defaultValue: defaultOllamaConnection,
  validate: (value) => {
    return value && typeof value.host === 'string' && typeof value.model === 'string'
  }
})

// Notification system
const notification = useNotification()

// Load data on component mount
onMounted(() => {
  loadFromStorage()
})

function saveConnection() {
  if (!ollamaConnection.value.model.trim()) {
    notification.showError('Model is required')
    return
  }

  const success = saveToStorage()
  if (success) {
    notification.showSuccess('Ollama connection saved successfully')
  } else {
    notification.showError('Failed to save connection')
  }
}

function testConnection() {
  console.log('Testing Ollama connection...', ollamaConnection.value)
  // TODO: Implement actual connection test
  notification.showSuccess('Connection test feature coming soon')
}
</script>

<template>
  <form class="form" @submit.prevent="saveConnection">
      <div class="form-group">
        <label for="ollama-host">Host</label>
        <input 
          id="ollama-host"
          v-model="ollamaConnection.host" 
          type="text" 
          class="form-input"
          placeholder="http://localhost:11434"
        />
        <small class="form-hint">Ollama server base URL</small>
      </div>

      <div class="form-group">
        <label for="ollama-route">Route</label>
        <select id="ollama-route" v-model="ollamaConnection.route" class="form-select">
          <option value="/api/chat">/api/chat</option>
          <option value="/api/generate">/api/generate</option>
        </select>
        <small class="form-hint">Use /api/chat for message arrays; /api/generate for single-prompt completion</small>
      </div>

      <div class="form-group">
        <label for="ollama-model">Model *</label>
        <input 
          id="ollama-model"
          v-model="ollamaConnection.model" 
          type="text" 
          class="form-input"
          placeholder="llama3:8b"
          required
        />
        <small class="form-hint">Local model name, e.g. llama3:8b or mistral:7b</small>
      </div>

      <div class="form-group">
        <label for="ollama-keep-alive">Keep Alive</label>
        <input 
          id="ollama-keep-alive"
          v-model="ollamaConnection.keep_alive" 
          type="text" 
          class="form-input"
          placeholder="5m"
        />
        <small class="form-hint">Keep model in memory after requests (e.g., 5m, 0 to unload)</small>
      </div>

      <div class="form-group">
        <label class="form-checkbox-label">
          <input 
            v-model="ollamaConnection.stream" 
            type="checkbox" 
            class="form-checkbox"
          />
          <span class="form-checkbox-custom"></span>
          Stream responses
        </label>
      </div>

      <div class="form-group">
        <label for="ollama-format">Format</label>
        <select id="ollama-format" v-model="ollamaConnection.format" class="form-select">
          <option :value="null">None</option>
          <option value="json">JSON</option>
        </select>
        <small class="form-hint">Enable JSON mode. Remember to also instruct the model to answer in JSON</small>
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