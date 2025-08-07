<script setup lang="ts">
import { ref } from 'vue'
import NewModule from './NewModule.vue'

const showNewModule = ref(false)

function createNewModule() {
  showNewModule.value = true
}

function goBackToModules() {
  showNewModule.value = false
}
</script>

<template>
  <div class="view-container">
    <NewModule v-if="showNewModule" @back="goBackToModules" />
    <div v-else class="modules-content">
      <h1>Modules</h1>
      <div class="content-area">
        <!-- Module list will go here -->
      </div>
      <div class="controls-section">
        <div class="action-buttons">
          <button class="action-btn new-btn" @click="createNewModule">
            <i class="fa-solid fa-plus"></i>
            New
          </button>
          <button class="action-btn edit-btn">
            <i class="fa-solid fa-edit"></i>
            Edit
          </button>
          <button class="action-btn delete-btn">
            <i class="fa-solid fa-trash"></i>
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';

.view-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.modules-content {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

h1 {
  color: var(--fg);
  font-size: 1.6em;
  font-weight: 600;
  margin-bottom: 16px;
  text-align: center;
}

.content-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--fg);
  opacity: 0.6;
}

.action-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: center;
}
</style>