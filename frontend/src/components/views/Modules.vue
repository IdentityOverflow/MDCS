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
      <button class="create-btn" @click="createNewModule">
        <i class="fa-solid fa-plus"></i>
        Create New Module
      </button>
    </div>
  </div>
</template>

<style scoped>
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

.create-btn {
  background: #B12C00;
  border: 1px solid var(--border);
  color: white;
  border-radius: 8px;
  padding: 12px 16px;
  cursor: pointer;
  font-size: 1em;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  align-self: center;
  transition: background-color 0.2s;
}

.create-btn:hover {
  background: #EB5B00;
}

.create-btn:active {
  background: #9A2400;
}

.create-btn i {
  font-size: 1.1em;
}
</style>