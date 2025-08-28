<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useModules } from '@/composables/useModules'
import { useNotification } from '@/composables/storage'
import type { ModuleCreateRequest, ModuleUpdateRequest, Module } from '@/types'
import CodeEditor from '@/components/CodeEditor.vue'

const props = defineProps<{
  editingModuleId?: string | null
}>()

const emit = defineEmits<{
  back: []
}>()

// Form data
const formData = ref<ModuleCreateRequest>({
  name: '',
  description: '',
  content: '',
  type: 'simple',
  trigger_pattern: '',
  script: '',
  execution_context: 'ON_DEMAND'
})

const loading = ref(false)
const isEditing = ref(false)
const moduleMetadata = ref<{
  created_at?: string
  updated_at?: string
} | null>(null)

// Script testing state
const testingScript = ref(false)
const testResult = ref<{
  success: boolean
  resolved_content?: string
  outputs?: Record<string, any>
  error?: string
  traceback?: string
} | null>(null)

// Module name validation
const nameValidation = ref({
  isValid: true,
  message: ''
})

// Use the modules composable
const {
  getModule,
  createModule,
  updateModule,
  error,
  clearError
} = useModules()

// Notification system
const notification = useNotification()

// Module name validation function
function validateModuleName(name: string): { isValid: boolean; message: string } {
  if (!name.trim()) {
    return { isValid: false, message: 'Module name is required' }
  }
  
  // Check length (max 50 characters)
  if (name.length > 50) {
    return { isValid: false, message: 'Module name must be 50 characters or less' }
  }
  
  // Check pattern: starts with letter, contains only a-z, 0-9, _
  const pattern = /^[a-z][a-z0-9_]*$/
  if (!pattern.test(name)) {
    return { 
      isValid: false, 
      message: 'Module name must start with a letter and contain only lowercase letters, numbers, and underscores' 
    }
  }
  
  return { isValid: true, message: '' }
}

// Reactive name validation
function onNameChange() {
  const result = validateModuleName(formData.value.name)
  nameValidation.value = result
}

// Load module data if editing
onMounted(async () => {
  if (props.editingModuleId) {
    isEditing.value = true
    await loadModuleForEditing(props.editingModuleId)
  }
})

async function loadModuleForEditing(id: string) {
  loading.value = true
  
  try {
    const module = await getModule(id)
    
    if (module) {
      formData.value = {
        name: module.name,
        description: module.description || '',
        content: module.content || '',
        type: module.type,
        trigger_pattern: module.trigger_pattern || '',
        script: module.script || '',
        execution_context: module.execution_context || 'ON_DEMAND'
      }
      
      moduleMetadata.value = {
        created_at: module.created_at,
        updated_at: module.updated_at
      }
    } else {
      notification.showError('Module not found')
      emit('back')
    }
  } catch (err) {
    notification.showError('Failed to load module for editing')
    emit('back')
  } finally {
    loading.value = false
  }
}

function goBack() {
  emit('back')
}

async function saveModule() {
  if (!validateForm()) {
    return
  }
  
  loading.value = true
  clearError()
  
  try {
    let result: Module | null = null
    
    if (isEditing.value && props.editingModuleId) {
      // Update existing module
      const updateData: ModuleUpdateRequest = { ...formData.value }
      result = await updateModule(props.editingModuleId, updateData)
    } else {
      // Create new module
      result = await createModule(formData.value)
    }
    
    if (result) {
      const action = isEditing.value ? 'updated' : 'created'
      notification.showSuccess(`Module ${action} successfully!`)
      emit('back')
    } else if (error.value) {
      notification.showError(`Failed to ${isEditing.value ? 'update' : 'create'} module: ${error.value}`)
    }
    
  } catch (err) {
    notification.showError(`Unexpected error: ${err instanceof Error ? err.message : 'Unknown error'}`)
  } finally {
    loading.value = false
  }
}

function validateForm(): boolean {
  // Validate module name
  const nameResult = validateModuleName(formData.value.name)
  if (!nameResult.isValid) {
    notification.showError(nameResult.message)
    return false
  }
  
  // Content is now optional - no validation needed
  
  return true
}

function formatDateTime(dateString: string): string {
  try {
    const date = new Date(dateString)
    return date.toLocaleString()
  } catch {
    return dateString
  }
}

async function testScript() {
  if (!formData.value.script?.trim()) {
    notification.showError('Please enter a script to test')
    return
  }
  
  testingScript.value = true
  testResult.value = null
  clearError()
  
  try {
    const response = await fetch('http://localhost:8000/api/modules/test-script', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        script: formData.value.script,
        content: formData.value.content || ''
      })
    })
    
    if (!response.ok) {
      const errorData = await response.text()
      throw new Error(`HTTP ${response.status}: ${errorData}`)
    }
    
    const result = await response.json()
    testResult.value = result
    
    if (result.success) {
      notification.showSuccess('Script executed successfully!')
    } else {
      notification.showError('Script execution failed')
    }
    
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Unknown error'
    notification.showError(`Failed to test script: ${errorMessage}`)
    testResult.value = {
      success: false,
      error: errorMessage
    }
  } finally {
    testingScript.value = false
  }
}

function clearTestResult() {
  testResult.value = null
}
</script>

<template>
  <div class="form-container">
    <div class="form-header">
      <button class="action-btn form-back-btn" @click="goBack">
        <i class="fa-solid fa-arrow-left"></i>
        Back
      </button>
      <h1 class="form-title">{{ isEditing ? 'Edit Module' : 'New Module' }}</h1>
    </div>
    <div class="form-content-area">
      <form class="form" @submit.prevent>
        <!-- UUID (only shown when editing) -->
        <div v-if="isEditing && props.editingModuleId" class="form-group">
          <label>ID</label>
          <input 
            type="text" 
            :value="props.editingModuleId" 
            readonly 
            class="form-input readonly"
            title="Database-generated UUID (read-only)"
          >
        </div>

        <!-- Name -->
        <div class="form-group">
          <label>Name</label>
          <input 
            type="text" 
            v-model="formData.name"
            @input="onNameChange"
            placeholder="Enter module name (e.g. my_module, greeting_v2)"
            :class="['form-input', { 'invalid': !nameValidation.isValid && formData.name.length > 0 }]"
          >
          <div v-if="!nameValidation.isValid && formData.name.length > 0" class="validation-message">
            {{ nameValidation.message }}
          </div>
          <div v-else class="validation-help">
            Must start with a letter and contain only lowercase letters, numbers, and underscores (max 50 chars)
          </div>
        </div>

        <!-- Description -->
        <div class="form-group">
          <label>Description</label>
          <textarea 
            v-model="formData.description"
            placeholder="Enter module description"
            rows="3"
            class="form-textarea"
          ></textarea>
        </div>

        <!-- Content -->
        <div class="form-group">
          <label>Content (Optional)</label>
          <textarea 
            v-model="formData.content"
            placeholder="Enter module content (leave empty for dynamic modules)"
            rows="6"
            class="form-textarea"
          ></textarea>
        </div>

        <!-- Type -->
        <div class="form-group">
          <label>Type</label>
          <select v-model="formData.type" class="form-select">
            <option value="simple">Simple</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>

        <!-- Advanced fields (only when type is advanced) -->
        <div v-if="formData.type === 'advanced'" class="form-advanced-section">
          <!-- Trigger Pattern -->
          <div class="form-group">
            <label>Trigger Pattern</label>
            <input 
              type="text" 
              v-model="formData.trigger_pattern"
              placeholder="Enter trigger pattern"
              class="form-input"
            >
          </div>

          <!-- Script -->
          <div class="form-group">
            <div class="script-header">
              <label>Script</label>
              <button 
                type="button" 
                class="test-script-btn"
                @click="testScript"
                :disabled="testingScript || !formData.script?.trim()"
                title="Test the Python script"
              >
                <i v-if="testingScript" class="fa-solid fa-spinner fa-spin"></i>
                <i v-else class="fa-solid fa-play"></i>
                {{ testingScript ? 'Testing...' : 'Test Script' }}
              </button>
            </div>
            <CodeEditor 
              v-model="formData.script"
              placeholder="Enter Python script content"
            />
            
            <!-- Test Results -->
            <div v-if="testResult" class="test-result-container">
              <div class="test-result-header">
                <div class="result-status" :class="{ 'success': testResult.success, 'error': !testResult.success }">
                  <i :class="testResult.success ? 'fa-solid fa-check-circle' : 'fa-solid fa-exclamation-triangle'"></i>
                  {{ testResult.success ? 'Script Valid' : 'Script Error' }}
                </div>
                <button 
                  type="button" 
                  class="close-result-btn"
                  @click="clearTestResult"
                  title="Clear test results"
                >
                  <i class="fa-solid fa-times"></i>
                </button>
              </div>
              
              <!-- Success Results -->
              <div v-if="testResult.success" class="success-result">
                <div v-if="testResult.outputs && Object.keys(testResult.outputs).length > 0" class="outputs-section">
                  <h4>Script Outputs:</h4>
                  <div class="outputs-grid">
                    <div 
                      v-for="[key, value] in Object.entries(testResult.outputs)" 
                      :key="key"
                      class="output-item"
                    >
                      <span class="output-key">${{ key }}</span>
                      <span class="output-value">{{ String(value) }}</span>
                    </div>
                  </div>
                </div>
                
                <div v-if="testResult.resolved_content && testResult.resolved_content !== formData.content" class="resolved-content-section">
                  <h4>Resolved Content:</h4>
                  <pre class="resolved-content">{{ testResult.resolved_content }}</pre>
                </div>
              </div>
              
              <!-- Error Results -->
              <div v-if="!testResult.success" class="error-result">
                <div v-if="testResult.error" class="error-message">
                  <h4>Error:</h4>
                  <pre>{{ testResult.error }}</pre>
                </div>
                
                <div v-if="testResult.traceback" class="traceback">
                  <h4>Traceback:</h4>
                  <pre>{{ testResult.traceback }}</pre>
                </div>
              </div>
            </div>
          </div>

          <!-- Execution Context -->
          <div class="form-group">
            <label>Execution Context</label>
            <select v-model="formData.execution_context" class="form-select">
              <option value="IMMEDIATE">Before Response (IMMEDIATE)</option>
              <option value="POST_RESPONSE">After Response (POST_RESPONSE)</option>
              <option value="ON_DEMAND">On Demand (ON_DEMAND)</option>
            </select>
            <div class="execution-context-help">
              Choose when this module should execute relative to AI response generation
            </div>
          </div>
        </div>

        <!-- Module Metadata (only shown when editing) -->
        <div v-if="isEditing && moduleMetadata" class="form-group metadata-section">
          <label>Module Information</label>
          <div class="metadata-grid">
            <div class="metadata-item">
              <span class="metadata-label">Created:</span>
              <span class="metadata-value">{{ formatDateTime(moduleMetadata.created_at || '') }}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Last Updated:</span>
              <span class="metadata-value">{{ formatDateTime(moduleMetadata.updated_at || '') }}</span>
            </div>
          </div>
        </div>

        <!-- Form Actions -->
        <div class="form-actions">
          <button type="button" class="action-btn cancel-btn" @click="goBack" :disabled="loading">
            Cancel
          </button>
          <button type="button" class="action-btn save-btn" @click="saveModule" :disabled="loading">
            <i v-if="loading" class="fa-solid fa-spinner fa-spin"></i>
            <i v-else class="fa-solid fa-save"></i>
            {{ loading ? 'Saving...' : (isEditing ? 'Update Module' : 'Save Module') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';
@import '@/assets/form.css';

/* Module Metadata Section */
.metadata-section {
  background: rgba(0, 212, 255, 0.03);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 0;
  padding: 16px;
  margin-top: 20px;
  clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%);
}

.metadata-section label {
  color: var(--accent);
  font-size: 0.85em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
  display: block;
}

.metadata-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.metadata-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metadata-label {
  color: var(--fg);
  font-size: 0.8em;
  font-weight: 600;
  opacity: 0.7;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.metadata-value {
  color: var(--fg);
  font-size: 0.85em;
  font-weight: 500;
  opacity: 0.9;
  font-family: monospace;
  background: rgba(0, 0, 0, 0.2);
  padding: 4px 8px;
  border-radius: 2px;
  border: 1px solid rgba(0, 212, 255, 0.1);
}

/* Enhanced readonly input styling */
.form-input.readonly {
  background: var(--surface);
  color: var(--accent);
  opacity: 0.8;
  cursor: not-allowed;
  font-family: monospace;
  font-size: 0.9em;
  border: 1px solid rgba(0, 212, 255, 0.2);
}

.form-input.readonly::selection {
  background: rgba(0, 212, 255, 0.3);
}

/* Module name validation styles */
.form-input.invalid {
  border-color: #ff4757;
  box-shadow: 0 0 0 2px rgba(255, 71, 87, 0.2);
}

.validation-message {
  color: #ff4757;
  font-size: 0.8em;
  margin-top: 4px;
  font-weight: 500;
}

.validation-help {
  color: var(--fg);
  opacity: 0.6;
  font-size: 0.75em;
  margin-top: 4px;
  font-style: italic;
}

/* Script testing styles */
.script-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.test-script-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: linear-gradient(135deg, var(--accent) 0%, #ff4757 100%);
  border: 1px solid var(--accent);
  color: white;
  border-radius: 2px;
  font-size: 0.8em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: all 0.2s ease;
  clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 50%, calc(100% - 8px) 100%, 0 100%);
}

.test-script-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #ff4757 0%, var(--accent) 100%);
  box-shadow: 0 0 8px rgba(255, 0, 110, 0.4);
  transform: translateY(-1px);
}

.test-script-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.test-result-container {
  margin-top: 12px;
  background: var(--surface);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 2px;
  overflow: hidden;
}

.test-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(0, 212, 255, 0.05);
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.result-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 0.85em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.result-status.success {
  color: #00ff41;
}

.result-status.error {
  color: #ff4757;
}

.close-result-btn {
  background: none;
  border: none;
  color: var(--fg);
  cursor: pointer;
  padding: 4px;
  border-radius: 2px;
  transition: all 0.2s ease;
  opacity: 0.6;
}

.close-result-btn:hover {
  background: rgba(255, 71, 87, 0.2);
  color: #ff4757;
  opacity: 1;
}

.success-result, .error-result {
  padding: 12px;
}

.outputs-section h4, .resolved-content-section h4, .error-message h4, .traceback h4 {
  color: var(--accent);
  font-size: 0.8em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.outputs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px;
  margin-bottom: 16px;
}

.output-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: rgba(0, 0, 0, 0.2);
  padding: 8px;
  border-radius: 2px;
  border: 1px solid rgba(0, 212, 255, 0.1);
}

.output-key {
  color: var(--accent);
  font-size: 0.8em;
  font-weight: 600;
  font-family: monospace;
}

.output-value {
  color: var(--fg);
  font-size: 0.85em;
  font-family: monospace;
  background: rgba(0, 0, 0, 0.2);
  padding: 4px;
  border-radius: 2px;
  border: 1px solid rgba(0, 212, 255, 0.05);
  word-break: break-word;
}

.resolved-content, .error-message pre, .traceback pre {
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 2px;
  border: 1px solid rgba(0, 212, 255, 0.1);
  color: var(--fg);
  font-size: 0.8em;
  font-family: 'Fira Code', monospace;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-x: auto;
  margin: 0;
}

.error-message pre, .traceback pre {
  color: #ff4757;
  border-color: rgba(255, 71, 87, 0.2);
  background: rgba(255, 71, 87, 0.05);
}

.resolved-content {
  color: #00ff41;
  border-color: rgba(0, 255, 65, 0.2);
  background: rgba(0, 255, 65, 0.05);
}

.error-result {
  border-top: 1px solid rgba(255, 71, 87, 0.2);
}

.success-result {
  border-top: 1px solid rgba(0, 255, 65, 0.2);
}

/* Execution context help */
.execution-context-help {
  color: var(--fg);
  opacity: 0.6;
  font-size: 0.75em;
  margin-top: 4px;
  font-style: italic;
}
</style>