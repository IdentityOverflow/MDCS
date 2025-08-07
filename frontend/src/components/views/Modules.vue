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
  background: linear-gradient(135deg, var(--accent) 0%, #e91e63 100%);
  border: 1px solid var(--accent);
  border-left: 3px solid white;
  color: white;
  border-radius: 0;
  padding: 12px 16px;
  cursor: pointer;
  font-size: 1em;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 8px;
  align-self: center;
  transition: all 0.3s ease;
  box-shadow: 0 0 15px rgba(255, 0, 110, 0.3);
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%);
  position: relative;
}

.create-btn::before {
  content: '';
  position: absolute;
  bottom: 9px;
  right: 0;
  width: 17px;
  height: 1px;
  background: var(--accent);
  transform: rotate(-45deg);
  transform-origin: right center;
}


.create-btn:hover {
  background: linear-gradient(135deg, #e91e63 0%, var(--accent) 100%);
  box-shadow: 0 0 20px rgba(255, 0, 110, 0.5);
  transform: translateY(-2px);
}

.create-btn:active {
  transform: translateY(0);
  box-shadow: 0 0 10px rgba(255, 0, 110, 0.3);
}

.create-btn i {
  font-size: 1.1em;
}
</style>