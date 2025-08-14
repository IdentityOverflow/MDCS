<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { generateUniqueId } from '@/composables/utils'

const emit = defineEmits<{
  back: []
}>()

// Form data
const formData = ref({
  id: '',
  name: '',
  description: '',
  content: '',
  type: 'simple' as 'simple' | 'advanced',
  trigger_pattern: '',
  script: '',
  timing: 'before' as 'before' | 'after' | 'custom'
})

// Generate unique ID on mount
onMounted(() => {
  formData.value.id = generateUniqueId('module')
})


function goBack() {
  emit('back')
}

function saveModule() {
  console.log('Module form data:', JSON.stringify(formData.value, null, 2))
}
</script>

<template>
  <div class="form-container">
    <div class="form-header">
      <button class="action-btn form-back-btn" @click="goBack">
        <i class="fa-solid fa-arrow-left"></i>
        Back
      </button>
      <h1 class="form-title">New Module</h1>
    </div>
    <div class="form-content-area">
      <form class="form" @submit.prevent>
        <!-- ID -->
        <div class="form-group">
          <label>ID</label>
          <input 
            type="text" 
            :value="formData.id" 
            readonly 
            class="form-input readonly"
          >
        </div>

        <!-- Name -->
        <div class="form-group">
          <label>Name</label>
          <input 
            type="text" 
            v-model="formData.name"
            placeholder="Enter module name"
            class="form-input"
          >
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
          <label>Content</label>
          <textarea 
            v-model="formData.content"
            placeholder="Enter module content"
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
              <option value="custom">Custom</option>
            </select>
          </div>
        </div>

        <!-- Form Actions -->
        <div class="form-actions">
          <button type="button" class="action-btn cancel-btn" @click="goBack">Cancel</button>
          <button type="button" class="action-btn save-btn" @click="saveModule">Save Module</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';
@import '@/assets/form.css';
</style>