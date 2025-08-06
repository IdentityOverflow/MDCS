<script setup lang="ts">
import { ref, onMounted } from 'vue'

const emit = defineEmits<{
  back: []
}>()

// Form data
const formData = ref({
  id: '',
  name: '',
  description: '',
  template: '',
  mode: 'reactive' as 'autonomous' | 'reactive',
  loop_frequency: 5.0,
  first_message: '',
  image: null as File | null
})

const imagePreview = ref('')
const dragOver = ref(false)
const fileInput = ref<HTMLInputElement>()

// Generate unique ID on mount
onMounted(() => {
  formData.value.id = generateUniqueId()
})

function generateUniqueId(): string {
  return 'persona_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now().toString(36)
}

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

</script>

<template>
  <div class="new-persona-container">
    <div class="header">
      <button class="back-btn" @click="goBack">
        <i class="fa-solid fa-arrow-left"></i>
        Back
      </button>
      <h1>New Persona</h1>
    </div>
    <div class="content-area">
      <form class="persona-form" @submit.prevent>
        <!-- Image Upload -->
        <div class="form-group">
          <label>Image</label>
          <div 
            class="image-drop-area"
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
            <div v-if="imagePreview" class="image-preview">
              <img :src="imagePreview" alt="Preview" />
            </div>
            <div v-else class="drop-placeholder">
              <i class="fa-solid fa-cloud-upload-alt"></i>
              <p>Drag & drop an image here or click to browse</p>
              <small>Supports: PNG, JPG, GIF</small>
            </div>
          </div>
        </div>

        <!-- ID -->
        <div class="form-group">
          <label>ID</label>
          <input 
            type="text" 
            :value="formData.id" 
            readonly 
            class="readonly-input"
          >
        </div>

        <!-- Name -->
        <div class="form-group">
          <label>Name</label>
          <input 
            type="text" 
            v-model="formData.name"
            placeholder="Enter persona name"
          >
        </div>

        <!-- Description -->
        <div class="form-group">
          <label>Description</label>
          <textarea 
            v-model="formData.description"
            placeholder="Enter persona description"
            rows="3"
          ></textarea>
        </div>

        <!-- Template -->
        <div class="form-group">
          <label>Template</label>
          <textarea 
            v-model="formData.template"
            placeholder="Enter persona template"
            rows="8"
          ></textarea>
        </div>

        <!-- Mode -->
        <div class="form-group">
          <label>Mode</label>
          <select v-model="formData.mode">
            <option value="reactive">Reactive</option>
            <option value="autonomous">Autonomous</option>
          </select>
        </div>

        <!-- Loop Frequency (only for autonomous mode) -->
        <div v-if="formData.mode === 'autonomous'" class="form-group">
          <label>Loop Frequency</label>
          <div class="framerate-input">
            <input 
              type="number" 
              v-model.number="formData.loop_frequency"
              step="0.1"
              min="0.1"
            >
            <span class="unit">Hz</span>
          </div>
        </div>

        <!-- First Message -->
        <div class="form-group">
          <label>First Message</label>
          <textarea 
            v-model="formData.first_message"
            placeholder="Enter first message (optional)"
            rows="3"
          ></textarea>
        </div>

        <!-- Form Actions -->
        <div class="form-actions">
          <button type="button" class="cancel-btn" @click="goBack">Cancel</button>
          <button type="submit" class="save-btn">Save Persona</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.new-persona-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 24px;
  position: relative;
}

.back-btn {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--fg);
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 0.9em;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
  position: absolute;
  left: 0;
}

.back-btn:hover {
  background: var(--surface);
  border-color: var(--fg);
}

h1 {
  color: var(--fg);
  font-size: 1.6em;
  font-weight: 600;
  margin: 0;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 0 4px;
}

.persona-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

label {
  color: var(--fg);
  font-weight: 600;
  font-size: 0.9em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

input, textarea, select {
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--fg);
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 0.95em;
  transition: border-color 0.2s;
}

input:focus, textarea:focus, select:focus {
  outline: none;
  border-color: #B12C00;
}

.readonly-input {
  background: var(--surface);
  color: var(--fg);
  opacity: 0.7;
  cursor: not-allowed;
}

textarea {
  resize: vertical;
  min-height: 80px;
}

select {
  cursor: pointer;
}

.image-drop-area {
  border: 2px dashed var(--border);
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-drop-area:hover,
.image-drop-area.drag-over {
  border-color: #B12C00;
  background: rgba(177, 44, 0, 0.05);
}

.drop-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--fg);
  opacity: 0.7;
}

.drop-placeholder i {
  font-size: 2em;
  color: #B12C00;
}

.drop-placeholder p {
  margin: 0;
  font-weight: 500;
}

.drop-placeholder small {
  font-size: 0.8em;
  opacity: 0.6;
}

.image-preview {
  max-width: 100%;
  max-height: 200px;
}

.image-preview img {
  max-width: 100%;
  max-height: 200px;
  object-fit: contain;
  border-radius: 4px;
}


.framerate-input {
  display: flex;
  align-items: center;
  gap: 8px;
}

.framerate-input input {
  flex: 1;
  max-width: 100px;
}

.unit {
  color: var(--fg);
  font-weight: 500;
  opacity: 0.8;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}

.cancel-btn {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--fg);
  border-radius: 8px;
  padding: 12px 20px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.cancel-btn:hover {
  background: var(--surface);
  border-color: var(--fg);
}

.save-btn {
  background: #B12C00;
  border: 1px solid #B12C00;
  color: white;
  border-radius: 8px;
  padding: 12px 20px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s;
}

.save-btn:hover {
  background: #EB5B00;
}

.save-btn:active {
  background: #9A2400;
}
</style>