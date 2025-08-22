<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useModules } from '@/composables/useModules'
import { useNotification } from '@/composables/storage'
import type { ModuleCreateRequest, ModuleUpdateRequest, Module } from '@/types'

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
  timing: 'custom'
})

const loading = ref(false)
const isEditing = ref(false)
const moduleMetadata = ref<{
  created_at?: string
  updated_at?: string
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
        timing: module.timing || 'custom'
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
            <label>Script</label>
            <textarea 
              v-model="formData.script"
              placeholder="Enter script content"
              rows="4"
              class="form-textarea"
            ></textarea>
          </div>

          <!-- Timing -->
          <div class="form-group">
            <label>Timing</label>
            <select v-model="formData.timing" class="form-select">
              <option value="before">Before</option>
              <option value="after">After</option>
              <option value="custom">On demand</option>
            </select>
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
</style>