<script setup lang="ts">
import { ref } from 'vue'

// PostgreSQL database connection form data
const databaseConnection = ref({
  host: 'localhost',
  port: 5432,
  database: '',
  username: '',
  password: '',
  ssl_mode: 'prefer',
  connection_timeout: 30,
  max_connections: 10,
  idle_timeout: 300
})

function saveConnection() {
  console.log('Saving Database connection:', databaseConnection.value)
  // TODO: Send to backend
}

function testConnection() {
  console.log('Testing Database connection...')
  // TODO: Test connection
}
</script>

<template>
  <form class="form" @submit.prevent="saveConnection">
      <div class="form-group">
        <label for="db-host">Host</label>
        <input 
          id="db-host"
          v-model="databaseConnection.host" 
          type="text" 
          class="form-input"
          placeholder="localhost"
        />
        <small class="form-hint">Database server hostname or IP address</small>
      </div>

      <div class="form-group">
        <label for="db-port">Port</label>
        <input 
          id="db-port"
          v-model.number="databaseConnection.port" 
          type="number" 
          class="form-input"
          min="1"
          max="65535"
          placeholder="5432"
        />
        <small class="form-hint">Database server port (default: 5432)</small>
      </div>

      <div class="form-group">
        <label for="db-database">Database *</label>
        <input 
          id="db-database"
          v-model="databaseConnection.database" 
          type="text" 
          class="form-input"
          placeholder="project2501"
          required
        />
        <small class="form-hint">Name of the database to connect to</small>
      </div>

      <div class="form-group">
        <label for="db-username">Username *</label>
        <input 
          id="db-username"
          v-model="databaseConnection.username" 
          type="text" 
          class="form-input"
          placeholder="postgres"
          required
        />
        <small class="form-hint">Database username</small>
      </div>

      <div class="form-group">
        <label for="db-password">Password *</label>
        <input 
          id="db-password"
          v-model="databaseConnection.password" 
          type="password" 
          class="form-input"
          placeholder="••••••••"
          required
        />
        <small class="form-hint">Database password</small>
      </div>

      <div class="form-group">
        <label for="db-ssl-mode">SSL Mode</label>
        <select id="db-ssl-mode" v-model="databaseConnection.ssl_mode" class="form-select">
          <option value="disable">Disable</option>
          <option value="allow">Allow</option>
          <option value="prefer">Prefer</option>
          <option value="require">Require</option>
          <option value="verify-ca">Verify CA</option>
          <option value="verify-full">Verify Full</option>
        </select>
        <small class="form-hint">SSL connection mode for secure connections</small>
      </div>

      <div class="form-group">
        <label for="db-connection-timeout">Connection Timeout (seconds)</label>
        <input 
          id="db-connection-timeout"
          v-model.number="databaseConnection.connection_timeout" 
          type="number" 
          class="form-input"
          min="1"
          max="300"
        />
        <small class="form-hint">Maximum time to wait for connection</small>
      </div>

      <div class="form-group">
        <label for="db-max-connections">Max Connections</label>
        <input 
          id="db-max-connections"
          v-model.number="databaseConnection.max_connections" 
          type="number" 
          class="form-input"
          min="1"
          max="100"
        />
        <small class="form-hint">Maximum number of concurrent connections</small>
      </div>

      <div class="form-group">
        <label for="db-idle-timeout">Idle Timeout (seconds)</label>
        <input 
          id="db-idle-timeout"
          v-model.number="databaseConnection.idle_timeout" 
          type="number" 
          class="form-input"
          min="1"
          max="3600"
        />
        <small class="form-hint">Time before idle connections are closed</small>
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
</template>

<style scoped>
@import '@/assets/buttons.css';
@import '@/assets/form.css';
</style>