<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  back: []
}>()

// Form data
const formData = ref({
  name: '',
  description: '',
  model: '',
  template: '',
  mode: 'reactive' as 'autonomous' | 'reactive',
  loop_frequency: 5.0,
  first_message: '',
  image: null as File | null
})

const imagePreview = ref('')
const dragOver = ref(false)
const fileInput = ref<HTMLInputElement>()



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

function handleFileSelect(file: File) {
  if (file.type.startsWith('image/')) {
    formData.value.image = file
    const reader = new FileReader()
    reader.onload = (e) => {
      imagePreview.value = e.target?.result as string
    }
    reader.readAsDataURL(file)
  }
}

function browseFiles() {
  fileInput.value?.click()
}

function savePersona() {
  // Create a serializable version of the form data
  const formDataForLogging = {
    ...formData.value,
    image: formData.value.image ? {
      name: formData.value.image.name,
      size: formData.value.image.size,
      type: formData.value.image.type,
      lastModified: formData.value.image.lastModified
    } : null
  }
  
  console.log('Persona form data:', JSON.stringify(formDataForLogging, null, 2))
}

</script>

<template>
  <div class="form-container">
    <div class="form-header">
      <button class="action-btn form-back-btn" @click="goBack">
        <i class="fa-solid fa-arrow-left"></i>
        Back
      </button>
      <h1 class="form-title">New Persona</h1>
    </div>
    <div class="form-content-area">
      <form class="form" @submit.prevent>
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

        <!-- Model -->
        <div class="form-group">
          <label>Model</label>
          <input 
            type="text" 
            v-model="formData.model"
            placeholder="Enter AI model (e.g. gpt-4, claude-3-sonnet)"
            class="form-input"
          >
        </div>

        <!-- Template -->
        <div class="form-group">
          <label>Template</label>
          <textarea 
            v-model="formData.template"
            placeholder="Enter persona template"
            rows="8"
            class="form-textarea"
          ></textarea>
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
          <button type="button" class="action-btn save-btn" @click="savePersona">Save Persona</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';
@import '@/assets/form.css';
</style>