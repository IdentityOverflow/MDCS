<script setup lang="ts">
import { ref, computed } from 'vue'
import { useDebug } from '@/composables/useDebug'
import DebugRecord from '@/components/DebugRecord.vue'

// Debug functionality
const { 
  debugRecords, 
  debugSettings, 
  recordsCount, 
  isAtMaxCapacity,
  clearDebugRecords,
  updateSettings 
} = useDebug()

// Local state for settings form
const maxRecordsInput = ref(debugSettings.value.maxRecords)
const enabledInput = ref(debugSettings.value.enabled)

// Computed for settings validation
const isValidMaxRecords = computed(() => {
  const value = maxRecordsInput.value
  return value >= 1 && value <= 50
})

const hasUnsavedChanges = computed(() => {
  return maxRecordsInput.value !== debugSettings.value.maxRecords ||
         enabledInput.value !== debugSettings.value.enabled
})

// Settings actions
const saveSettings = () => {
  if (!isValidMaxRecords.value) {
    alert('Max records must be between 1 and 50')
    return
  }

  updateSettings({
    maxRecords: maxRecordsInput.value,
    enabled: enabledInput.value
  })
}

const resetSettings = () => {
  maxRecordsInput.value = debugSettings.value.maxRecords
  enabledInput.value = debugSettings.value.enabled
}

// Clear all records with confirmation
const handleClearRecords = () => {
  if (recordsCount.value === 0) return
  
  const confirmed = confirm(
    `Are you sure you want to clear all ${recordsCount.value} debug records? This cannot be undone.`
  )
  
  if (confirmed) {
    clearDebugRecords()
  }
}
</script>

<template>
  <div class="debug-view">
    <div class="debug-header">
      <h2 class="debug-title">
        <i class="fa-solid fa-bug"></i>
        Debug Console
      </h2>
      <p class="debug-subtitle">
        AI Provider Request/Response Inspector
      </p>
    </div>

    <div class="debug-content">
      <!-- Settings Section -->
      <div class="debug-section">
        <h3 class="section-title">
          <i class="fa-solid fa-gear"></i>
          Settings
        </h3>
        
        <div class="settings-form">
          <div class="settings-row">
            <div class="setting-group">
              <label for="enabled-checkbox">
                <input 
                  id="enabled-checkbox"
                  type="checkbox" 
                  v-model="enabledInput"
                />
                <span>Enable Debug Recording</span>
              </label>
            </div>
            
            <div class="setting-group">
              <label for="max-records">Records to Keep:</label>
              <input 
                id="max-records"
                type="number" 
                v-model.number="maxRecordsInput"
                min="1"
                max="50"
                :class="{ invalid: !isValidMaxRecords }"
              />
              <span class="setting-hint">(1-50)</span>
            </div>
          </div>
          
          <div class="settings-actions">
            <button 
              class="action-btn dismiss-btn"
              @click="resetSettings"
              :disabled="!hasUnsavedChanges"
            >
              Reset
            </button>
            <button 
              class="action-btn create-btn"
              @click="saveSettings"
              :disabled="!hasUnsavedChanges || !isValidMaxRecords"
            >
              Save Settings
            </button>
          </div>
        </div>
      </div>

      <!-- Records Section -->
      <div class="debug-section">
        <div class="section-header">
          <h3 class="section-title">
            <i class="fa-solid fa-list"></i>
            Debug Records
            <span class="record-count">({{ recordsCount }}/{{ debugSettings.maxRecords }})</span>
          </h3>
          
          <button 
            class="action-btn"
            @click="handleClearRecords"
            :disabled="recordsCount === 0"
            style="border-left-color: #ff4757;"
          >
            <i class="fa-solid fa-trash"></i>
            Clear All
          </button>
        </div>

        <!-- Records List -->
        <div v-if="recordsCount > 0" class="records-list">
          <div v-if="isAtMaxCapacity" class="capacity-warning">
            <i class="fa-solid fa-exclamation-triangle"></i>
            Debug records at maximum capacity. Oldest records will be removed automatically.
          </div>
          
          <DebugRecord 
            v-for="record in debugRecords" 
            :key="record.id"
            :record="record"
          />
        </div>

        <!-- Empty State -->
        <div v-else class="empty-records">
          <div class="empty-records-content">
            <i class="fa-solid fa-inbox"></i>
            <h4>No Debug Records</h4>
            <p v-if="!debugSettings.enabled">
              Debug recording is disabled. Enable it in settings above.
            </p>
            <p v-else>
              Debug records will appear here when you send chat messages.
              Each record shows the exact request sent to the AI provider and its response.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';

.debug-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--fg);
}

.debug-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  background: rgba(0, 212, 255, 0.05);
}

.debug-title {
  margin: 0 0 4px 0;
  color: var(--accent);
  font-size: 1.2em;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.debug-subtitle {
  margin: 0;
  color: var(--fg);
  opacity: 0.7;
  font-size: 0.85em;
}

.debug-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.debug-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 16px;
}

.section-title {
  color: var(--accent);
  font-size: 1em;
  font-weight: 600;
  margin: 0 0 16px 0;
  display: flex;
  align-items: center;
  gap: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.record-count {
  color: var(--fg);
  opacity: 0.6;
  font-weight: normal;
  text-transform: none;
  letter-spacing: normal;
  font-size: 0.8em;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

/* Settings Form */
.settings-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-row {
  display: flex;
  gap: 24px;
  align-items: center;
  flex-wrap: wrap;
}

.setting-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.setting-group label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9em;
  color: var(--fg);
  cursor: pointer;
}

.setting-group input[type="number"] {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  color: var(--fg);
  font-size: 0.85em;
  width: 80px;
  text-align: center;
}

.setting-group input[type="number"]:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.2);
}

.setting-group input[type="number"].invalid {
  border-color: #ff4757;
  color: #ff4757;
}

.setting-hint {
  font-size: 0.75em;
  opacity: 0.6;
  color: var(--fg);
}

.settings-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

/* Custom action button adjustments */

/* Records List */
.records-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.capacity-warning {
  background: rgba(255, 167, 38, 0.1);
  border: 1px solid rgba(255, 167, 38, 0.3);
  border-radius: 4px;
  padding: 12px;
  color: #ffa726;
  font-size: 0.85em;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

/* Empty States */
.empty-records {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.empty-records-content {
  text-align: center;
  max-width: 400px;
}

.empty-records-content i {
  font-size: 3em;
  color: var(--accent);
  margin-bottom: 16px;
  display: block;
  opacity: 0.4;
}

.empty-records-content h4 {
  color: var(--accent);
  margin: 0 0 12px 0;
  font-size: 1em;
  font-weight: 600;
}

.empty-records-content p {
  color: var(--fg);
  opacity: 0.7;
  line-height: 1.4;
  margin: 0;
  font-size: 0.85em;
}
</style>