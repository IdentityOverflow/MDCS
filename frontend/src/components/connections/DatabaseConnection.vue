<script setup lang="ts">
import { useNotification } from '@/composables/storage'

// Notification system
const notification = useNotification()

async function testConnection() {
  console.log('Testing Database connection via backend...')
  
  try {
    const response = await fetch('http://localhost:8000/api/database/test', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const result = await response.json()
    
    if (result.status === 'success') {
      notification.showSuccess(`Database connected successfully! Database: ${result.database}, Version: ${result.version}`)
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
      <!-- Database Configuration Info -->
      <div class="info-section">
        <div class="info-header">
          <i class="fa-solid fa-info-circle"></i>
          <h3>Database Configuration</h3>
        </div>
        <div class="info-content">
          <p>The database connection is configured via environment variables on the backend server. 
          To set up the database connection, create or update the <code>.env</code> file in the backend directory with the following variables:</p>
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

      <div class="form-actions">
        <button type="button" @click="testConnection" class="action-btn save-btn">
          <i class="fa-solid fa-plug"></i>
          Test Connection
        </button>
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
</style>