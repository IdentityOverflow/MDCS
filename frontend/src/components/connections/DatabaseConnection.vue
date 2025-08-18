<script setup lang="ts">
import { useNotification } from '@/composables/storage'
import { useApiConfig } from '@/composables/apiConfig'

// Configuration and notification systems
const notification = useNotification()
const apiConfig = useApiConfig()

// Save API configuration
function saveApiConfig() {
  apiConfig.saveConfig()
  notification.showSuccess('API configuration saved successfully!')
}

// Reset API configuration to defaults
function resetApiConfig() {
  apiConfig.resetToDefaults()
  notification.showSuccess('API configuration reset to defaults')
}

async function testConnection() {
  console.log(`Testing Database connection via ${apiConfig.baseURL.value}...`)
  
  try {
    const response = await apiConfig.apiRequest('/api/database/test', {
      method: 'GET'
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const result = await response.json()
    
    if (result.status === 'success') {
      notification.showSuccess(`Database connected successfully! Database: ${result.database}`)
    } else {
      notification.showError(`Database connection failed: ${result.message}`)
    }
    
  } catch (error) {
    console.error('Database test failed:', error)
    notification.showError(`Connection test failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}
</script>

<template>
  <div class="form">
      <!-- Backend Setup Info -->
      <div class="info-section">
        <div class="info-header">
          <i class="fa-solid fa-info-circle"></i>
          <h3>Backend Setup</h3>
        </div>
        <div class="info-content">
          <p>Configure your backend connection and database. Create a <code>.env</code> file in the backend directory with database credentials.</p>
        </div>
      </div>

      <!-- Backend Connection Configuration -->
      <div class="connection-config">
        <h4 class="config-title">
          <i class="fa-solid fa-server"></i>
          Backend Connection
        </h4>
        
        <div class="form-row">
          <div class="form-group">
            <label for="api-protocol">Protocol</label>
            <select id="api-protocol" v-model="apiConfig.protocol.value" class="form-select">
              <option value="http">HTTP</option>
              <option value="https">HTTPS</option>
            </select>
          </div>

          <div class="form-group">
            <label for="api-host">Host</label>
            <input 
              id="api-host"
              type="text" 
              v-model="apiConfig.host.value" 
              class="form-input" 
              placeholder="localhost"
            />
          </div>

          <div class="form-group">
            <label for="api-port">Port</label>
            <input 
              id="api-port"
              type="number" 
              v-model.number="apiConfig.port.value" 
              class="form-input" 
              min="1" 
              max="65535"
              placeholder="8000"
            />
          </div>
        </div>

        <!-- Current URL Display -->
        <div class="form-group">
          <label>API Base URL</label>
          <div class="url-display">
            <code>{{ apiConfig.baseURL.value }}</code>
          </div>
        </div>

        <!-- Actions -->
        <div class="form-actions inline-actions">
          <button type="button" @click="saveApiConfig" class="action-btn save-btn">
            <i class="fa-solid fa-save"></i>
            Save
          </button>
          <button type="button" @click="resetApiConfig" class="action-btn secondary-btn">
            <i class="fa-solid fa-undo"></i>
            Reset
          </button>
          <button type="button" @click="testConnection" class="action-btn save-btn">
            <i class="fa-solid fa-plug"></i>
            Test Connection
          </button>
        </div>
      </div>

      <!-- .env Example -->
      <div class="form-group">
        <label>Required Environment Variables</label>
        <div class="code-block">
          <pre><code># Database connection settings
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=yourStrongPasswordHere

# Optional: connection URL format
DATABASE_URL=postgresql://postgres:yourStrongPasswordHere@localhost:5432/postgres</code></pre>
        </div>
        <small class="form-hint">Copy this template and update with your PostgreSQL database credentials</small>
      </div>

      <!-- Setup Instructions -->
      <div class="info-section">
        <div class="info-content">
          <h4>Setup Instructions:</h4>
          <ol>
            <li>Create a <code>.env</code> file in the backend directory</li>
            <li>Copy the environment variables above into the file</li>
            <li>Update the values with your actual database credentials</li>
            <li>Restart the backend server to apply changes</li>
            <li>Use the "Test Connection" button below to verify the connection</li>
          </ol>
        </div>
      </div>

  </div>
  
  <!-- Notification Toast -->
  <div v-if="notification.isVisible.value" class="notification-toast" :class="notification.type.value">
    <i :class="notification.type.value === 'success' ? 'fa-solid fa-check' : 'fa-solid fa-exclamation-triangle'"></i>
    {{ notification.message.value }}
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';
@import '@/assets/form.css';

.info-section {
  margin-bottom: 24px;
  padding: 16px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 0;
  clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%);
}

.info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.info-header i {
  color: var(--accent);
  font-size: 1.2em;
}

.info-header h3 {
  color: var(--fg);
  font-size: 1em;
  font-weight: 600;
  margin: 0;
}

.info-content {
  color: var(--fg);
  line-height: 1.5;
}

.info-content p {
  margin: 0 0 12px 0;
  opacity: 0.9;
}

.info-content h4 {
  color: var(--accent);
  font-size: 0.9em;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.info-content ol {
  margin: 0;
  padding-left: 20px;
  opacity: 0.9;
}

.info-content ol li {
  margin-bottom: 4px;
}

.info-content code {
  background: rgba(0, 255, 255, 0.1);
  color: var(--accent);
  padding: 2px 6px;
  border-radius: 2px;
  font-family: monospace;
  font-size: 0.9em;
}

.code-block {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 0;
  padding: 16px;
  margin: 8px 0;
  overflow-x: auto;
}

.code-block pre {
  margin: 0;
  color: var(--fg);
  font-family: monospace;
  font-size: 0.85em;
  line-height: 1.4;
}

.code-block code {
  background: none;
  color: inherit;
  padding: 0;
}

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

/* Connection Configuration Section */
.connection-config {
  background: rgba(0, 212, 255, 0.03);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 0;
  padding: 20px;
  margin: 16px 0;
  clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%);
}

.config-title {
  color: var(--accent);
  font-size: 1em;
  font-weight: 600;
  margin: 0 0 16px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Form Row Layout */
.form-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 16px;
  align-items: end;
  margin-bottom: 16px;
}

.form-row .form-group {
  margin: 0;
}

/* Override form-actions default justify-content for inline layout */
.form-actions.inline-actions {
  justify-content: flex-start;
}

/* URL Display */
.url-display {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 0;
  padding: 12px;
  margin: 8px 0;
  display: flex;
  align-items: center;
}

.url-display code {
  background: none;
  color: var(--accent);
  font-family: monospace;
  font-size: 0.9em;
  font-weight: 600;
  padding: 0;
}

/* Secondary Button */
.secondary-btn {
  background: var(--surface);
  color: var(--fg);
  border: 1px solid var(--border);
}

.secondary-btn:hover {
  background: rgba(0, 212, 255, 0.1);
  border-color: var(--accent);
}

.secondary-btn:active {
  background: rgba(0, 212, 255, 0.2);
}
</style>