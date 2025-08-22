<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { usePersonas } from '@/composables/usePersonas'
import TemplateEditor from '@/components/TemplateEditor.vue'
import type { PersonaCreateRequest, PersonaUpdateRequest } from '@/types'

const props = defineProps<{
  editingPersonaId?: string | null
}>()

const emit = defineEmits<{
  back: []
}>()

// Use personas composable
const {
  createPersona,
  updatePersona,
  fetchPersonaById,
  uploadPersonaImage,
  loading,
  error,
  clearError
} = usePersonas()

// Form data
const formData = ref({
  name: '',
  description: '',
  template: '',
  mode: 'reactive' as 'autonomous' | 'reactive',
  loop_frequency: 5.0,
  first_message: '',
  image_path: '' as string
})

const imagePreview = ref('')
const dragOver = ref(false)
const fileInput = ref<HTMLInputElement>()
const saving = ref(false)
const loadingPersona = ref(false)

// Template validation
const templateValidation = ref({
  isValid: true,
  warnings: [] as Array<{ type: string, message: string }>
})

// Template validation functions
function validateTemplate(template: string): { isValid: boolean; warnings: Array<{ type: string, message: string }> } {
  const warnings: Array<{ type: string, message: string }> = []
  
  if (!template.trim()) {
    return { isValid: false, warnings: [{ type: 'error', message: 'Template is required' }] }
  }
  
  // Parse @module_name references (but not escaped \@module_name)
  const modulePattern = /(?<!\\)@([a-z][a-z0-9_]*)/g
  const invalidPattern = /(?<!\\)@([^a-z\s][a-zA-Z0-9_]*|[A-Z][a-zA-Z0-9_]*|[a-z][a-zA-Z0-9_]*[A-Z][a-zA-Z0-9_]*)/g
  const moduleMatches = Array.from(template.matchAll(modulePattern))
  const invalidMatches = Array.from(template.matchAll(invalidPattern))
  
  // Check for invalid module name formats
  if (invalidMatches.length > 0) {
    const invalidNames = invalidMatches.map(match => `@${match[1]}`).join(', ')
    warnings.push({
      type: 'error',
      message: `Invalid module name format: ${invalidNames}. Module names must start with a letter and contain only lowercase letters, numbers, and underscores.`
    })
  }
  
  // Check for valid module references
  if (moduleMatches.length > 0) {
    const moduleNames = moduleMatches.map(match => match[1])
    const uniqueModules = [...new Set(moduleNames)]
    
    if (uniqueModules.length > 0) {
      warnings.push({
        type: 'info',
        message: `Found ${uniqueModules.length} module reference(s): ${uniqueModules.map(name => `@${name}`).join(', ')}`
      })
    }
    
    // Check for potential circular references (same module name in template)
    const duplicates = moduleNames.filter((name, index) => moduleNames.indexOf(name) !== index)
    if (duplicates.length > 0) {
      const uniqueDuplicates = [...new Set(duplicates)]
      warnings.push({
        type: 'warning', 
        message: `Module(s) referenced multiple times: ${uniqueDuplicates.map(name => `@${name}`).join(', ')}`
      })
    }
  }
  
  const hasErrors = warnings.some(w => w.type === 'error')
  return { isValid: !hasErrors, warnings }
}

function onTemplateChange() {
  const result = validateTemplate(formData.value.template)
  templateValidation.value = result
}

// Computed values
const isEditing = computed(() => !!props.editingPersonaId)
const formTitle = computed(() => isEditing.value ? 'Edit Persona' : 'New Persona')
const saveButtonText = computed(() => saving.value ? 'Saving...' : (isEditing.value ? 'Update Persona' : 'Save Persona'))

// Reset form
const resetForm = () => {
  formData.value = {
    name: '',
    description: '',
    template: '',
    mode: 'reactive',
    loop_frequency: 5.0,
    first_message: '',
    image_path: ''
  }
  imagePreview.value = ''
  clearError()
}

// Load persona for editing
const loadPersonaForEditing = async (personaId: string) => {
  loadingPersona.value = true
  try {
    const persona = await fetchPersonaById(personaId)
    
    formData.value = {
      name: persona.name,
      description: persona.description || '',
      template: persona.template,
      mode: persona.mode,
      loop_frequency: persona.loop_frequency ? parseFloat(persona.loop_frequency) : 5.0,
      first_message: persona.first_message || '',
      image_path: persona.image_path || ''
    }
    
    // Set image preview if persona has image
    if (persona.image_path) {
      imagePreview.value = persona.image_path.startsWith('/static/') 
        ? `http://localhost:8000${persona.image_path}` 
        : persona.image_path
    }
    
  } catch (err) {
    console.error('Failed to load persona for editing:', err)
    alert('Failed to load persona data. Please try again.')
    emit('back')
  } finally {
    loadingPersona.value = false
  }
}

// Watch for editing mode
watch(() => props.editingPersonaId, async (personaId) => {
  if (personaId) {
    await loadPersonaForEditing(personaId)
  } else {
    resetForm()
  }
}, { immediate: true })

function goBack() {
  emit('back')
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  dragOver.value = true
}

function handleDragLeave(e: DragEvent) {
  e.preventDefault()
  dragOver.value = false
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  dragOver.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    handleFileSelect(files[0])
  }
}

function handleFileInput(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    handleFileSelect(target.files[0])
  }
}

async function handleFileSelect(file: File) {
  if (file.type.startsWith('image/')) {
    try {
      // Show immediate preview
      const reader = new FileReader()
      reader.onload = (e) => {
        imagePreview.value = e.target?.result as string
      }
      reader.readAsDataURL(file)

      // Upload to server
      const imagePath = await uploadPersonaImage(file)
      formData.value.image_path = imagePath
      
      // Update preview to use server URL
      imagePreview.value = `http://localhost:8000${imagePath}`
      
      console.log('Image uploaded successfully:', imagePath)
    } catch (err) {
      console.error('Failed to upload image:', err)
      alert('Failed to upload image. Please try again.')
      // Reset image if upload failed
      imagePreview.value = ''
      formData.value.image_path = ''
    }
  }
}

function browseFiles() {
  fileInput.value?.click()
}

async function savePersona() {
  if (!formData.value.name.trim()) {
    alert('Please enter a persona name')
    return
  }
  
  // Validate template
  const templateResult = validateTemplate(formData.value.template)
  if (!templateResult.isValid) {
    const errorMessages = templateResult.warnings
      .filter(w => w.type === 'error')
      .map(w => w.message)
      .join('\n')
    alert(`Template validation failed:\n${errorMessages}`)
    return
  }
  
  saving.value = true
  clearError()
  
  try {
    // Prepare data for API 
    const personaData = {
      name: formData.value.name.trim(),
      description: formData.value.description.trim() || undefined,
      template: formData.value.template.trim(),
      mode: formData.value.mode,
      loop_frequency: formData.value.mode === 'autonomous' ? formData.value.loop_frequency.toString() : undefined,
      first_message: formData.value.first_message.trim() || undefined,
      image_path: formData.value.image_path || undefined
    }
    
    if (isEditing.value && props.editingPersonaId) {
      // Update existing persona
      await updatePersona(props.editingPersonaId, personaData as PersonaUpdateRequest)
      console.log('Persona updated successfully')
    } else {
      // Create new persona
      await createPersona(personaData as PersonaCreateRequest)
      console.log('Persona created successfully')
    }
    
    // Success - go back to list
    emit('back')
    
  } catch (err) {
    console.error('Error saving persona:', err)
    const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
    alert(`Failed to save persona: ${errorMessage}`)
  } finally {
    saving.value = false
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
      <h1 class="form-title">{{ formTitle }}</h1>
    </div>
    <div class="form-content-area">
      <!-- Loading State -->
      <div v-if="loadingPersona" class="loading-state">
        <i class="fa-solid fa-spinner fa-spin"></i>
        <p>Loading persona data...</p>
      </div>
      
      <form v-else class="form" @submit.prevent>
        <!-- UUID Display (Edit Mode Only) -->
        <div v-if="isEditing && editingPersonaId" class="form-group">
          <label>ID</label>
          <input type="text" :value="editingPersonaId" readonly class="form-input readonly">
        </div>

        <!-- Image Upload -->
        <div class="form-group">
          <label>Image</label>
          <div 
            class="form-image-drop-area"
            :class="{ 'drag-over': dragOver }"
            @dragover="handleDragOver"
            @dragleave="handleDragLeave"
            @drop="handleDrop"
            @click="browseFiles"
          >
            <input 
              ref="fileInput"
              type="file"
              accept="image/*,.gif"
              @change="handleFileInput"
              style="display: none"
            >
            <div v-if="imagePreview" class="form-image-preview">
              <img :src="imagePreview" alt="Preview" />
            </div>
            <div v-else class="form-drop-placeholder">
              <i class="fa-solid fa-cloud-upload-alt"></i>
              <p>Drag & drop an image here or click to browse</p>
              <small>Supports: PNG, JPG, GIF</small>
            </div>
          </div>
        </div>

        <!-- Name -->
        <div class="form-group">
          <label>Name</label>
          <input 
            type="text" 
            v-model="formData.name"
            placeholder="Enter persona name"
            class="form-input"
          >
        </div>

        <!-- Description -->
        <div class="form-group">
          <label>Description</label>
          <textarea 
            v-model="formData.description"
            placeholder="Enter persona description"
            rows="3"
            class="form-textarea"
          ></textarea>
        </div>

        <!-- Template -->
        <div class="form-group">
          <label>Template</label>
          <TemplateEditor
            v-model="formData.template"
            @input="onTemplateChange"
            placeholder="Enter persona template (use @module_name to reference modules)"
            rows="8"
            :invalid="!templateValidation.isValid && formData.template.length > 0"
          />
          <div v-if="templateValidation.warnings.length > 0" class="template-validation">
            <div 
              v-for="warning in templateValidation.warnings" 
              :key="warning.message"
              :class="['validation-message', warning.type]"
            >
              <i :class="['fa-solid', warning.type === 'error' ? 'fa-exclamation-circle' : warning.type === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle']"></i>
              {{ warning.message }}
            </div>
          </div>
          <div v-else class="validation-help">
            Reference modules using @module_name syntax (e.g., @greeting, @context_memory). Type @ to see available modules.<br>
            Use \@module_name to include literal @module_name text without module resolution.
          </div>
        </div>

        <!-- Mode -->
        <div class="form-group">
          <label>Mode</label>
          <select v-model="formData.mode" class="form-select">
            <option value="reactive">Reactive</option>
            <option value="autonomous">Autonomous</option>
          </select>
        </div>

        <!-- Loop Frequency (only for autonomous mode) -->
        <div v-if="formData.mode === 'autonomous'" class="form-group">
          <label>Loop Frequency</label>
          <div class="form-number-input">
            <input 
              type="number" 
              v-model.number="formData.loop_frequency"
              step="0.1"
              min="0.1"
              class="form-input"
            >
            <span class="form-unit">Hz</span>
          </div>
        </div>

        <!-- First Message -->
        <div class="form-group">
          <label>First Message</label>
          <textarea 
            v-model="formData.first_message"
            placeholder="Enter first message (optional)"
            rows="3"
            class="form-textarea"
          ></textarea>
        </div>

        <!-- Form Actions -->
        <div class="form-actions">
          <button type="button" class="action-btn cancel-btn" @click="goBack">Cancel</button>
          <button 
            type="button" 
            class="action-btn save-btn" 
            @click="savePersona"
            :disabled="saving || loadingPersona"
          >
            <i v-if="saving" class="fa-solid fa-spinner fa-spin"></i>
            {{ saveButtonText }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';
@import '@/assets/form.css';

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--fg-muted);
  text-align: center;
}

.loading-state i {
  font-size: 2em;
  margin-bottom: 16px;
  color: var(--accent);
}

/* Readonly Input */
.form-input.readonly {
  background-color: var(--bg-2);
  color: var(--fg-muted);
  cursor: not-allowed;
}

/* Template validation styles are now handled by TemplateEditor component */

.template-validation {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.validation-message {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8em;
  font-weight: 500;
}

.validation-message.error {
  color: #ff4757;
}

.validation-message.warning {
  color: #ffa726;
}

.validation-message.info {
  color: var(--accent);
}

.validation-help {
  color: var(--fg);
  opacity: 0.6;
  font-size: 0.75em;
  margin-top: 4px;
  font-style: italic;
}

</style>