<script setup lang="ts">
import { ref, onMounted } from 'vue'

const emit = defineEmits<{
  back: []
}>()

// Form data
const formData = ref({
  id: '',
  name: '',
  content: '',
  type: 'simple' as 'simple' | 'advanced',
  trigger_pattern: '',
  script: '',
  timing: 'before' as 'before' | 'after' | 'custom'
})

// Generate unique ID on mount
onMounted(() => {
  formData.value.id = generateUniqueId()
})

function generateUniqueId(): string {
  return 'module_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now().toString(36)
}

function goBack() {
  emit('back')
}
</script>

<template>
  <div class="new-module-container">
    <div class="header">
      <button class="back-btn" @click="goBack">
        <i class="fa-solid fa-arrow-left"></i>
        Back
      </button>
      <h1>New Module</h1>
    </div>
    <div class="content-area">
      <form class="module-form" @submit.prevent>
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
            placeholder="Enter module name"
          >
        </div>

        <!-- Content -->
        <div class="form-group">
          <label>Content</label>
          <textarea 
            v-model="formData.content"
            placeholder="Enter module content"
            rows="6"
          ></textarea>
        </div>

        <!-- Type -->
        <div class="form-group">
          <label>Type</label>
          <select v-model="formData.type">
            <option value="simple">Simple</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>

        <!-- Advanced fields (only when type is advanced) -->
        <div v-if="formData.type === 'advanced'" class="advanced-fields">
          <!-- Trigger Pattern -->
          <div class="form-group">
            <label>Trigger Pattern</label>
            <input 
              type="text" 
              v-model="formData.trigger_pattern"
              placeholder="Enter trigger pattern"
            >
          </div>

          <!-- Script -->
          <div class="form-group">
            <label>Script</label>
            <textarea 
              v-model="formData.script"
              placeholder="Enter script content"
              rows="4"
            ></textarea>
          </div>

          <!-- Timing -->
          <div class="form-group">
            <label>Timing</label>
            <select v-model="formData.timing">
              <option value="before">Before</option>
              <option value="after">After</option>
              <option value="custom">Custom</option>
            </select>
          </div>
        </div>

        <!-- Form Actions -->
        <div class="form-actions">
          <button type="button" class="cancel-btn" @click="goBack">Cancel</button>
          <button type="submit" class="save-btn">Save Module</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.new-module-container {
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

.module-form {
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

.advanced-fields {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  border: 2px dashed var(--border);
  border-radius: 8px;
  background: rgba(177, 44, 0, 0.02);
  position: relative;
}

.advanced-fields::before {
  content: "Advanced Options";
  position: absolute;
  top: -12px;
  left: 16px;
  background: var(--bg);
  color: #B12C00;
  padding: 0 8px;
  font-size: 0.8em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
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