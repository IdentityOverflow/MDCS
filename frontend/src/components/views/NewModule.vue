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
      <button class="action-btn back-btn" @click="goBack">
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
          <button type="button" class="action-btn cancel-btn" @click="goBack">Cancel</button>
          <button type="submit" class="action-btn save-btn">Save Module</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';

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
  position: absolute;
  left: 0;
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
  background: linear-gradient(135deg, var(--bg) 0%, var(--secondary) 100%);
  border: 1px solid var(--border);
  color: var(--fg);
  border-radius: 0;
  padding: 10px 12px;
  font-size: 0.95em;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: inset 0 0 5px rgba(0, 212, 255, 0.1);
}

input:focus, textarea:focus, select:focus {
  outline: none;
  border-color: var(--fg);
  box-shadow: 0 0 10px var(--glow), inset 0 0 10px rgba(0, 212, 255, 0.2);
  background: linear-gradient(135deg, var(--secondary) 0%, var(--bg) 100%);
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
  appearance: none;
  background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="12" height="8" viewBox="0 0 12 8"><path fill="%2300ffff" d="M6 8L0 0h12z"/></svg>');
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
}

select option {
  background: var(--surface);
  color: var(--fg);
  border: none;
  padding: 8px 12px;
}

.advanced-fields {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  border: 2px dashed var(--border);
  border-radius: 0;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.05) 0%, rgba(255, 0, 110, 0.05) 100%);
  position: relative;
  box-shadow: inset 0 0 15px rgba(0, 212, 255, 0.1);
}

.advanced-fields::before {
  content: "Advanced Options";
  position: absolute;
  top: -12px;
  left: 16px;
  background: var(--bg);
  color: var(--accent);
  padding: 0 8px;
  font-size: 0.8em;
  font-weight: 700;
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
</style>