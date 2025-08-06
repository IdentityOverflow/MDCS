<script setup lang="ts">
import { ref } from 'vue'
import NewPersona from './NewPersona.vue'

const showNewPersona = ref(false)

function createNewPersona() {
  showNewPersona.value = true
}

function goBackToPersonas() {
  showNewPersona.value = false
}
</script>

<template>
  <div class="view-container">
    <NewPersona v-if="showNewPersona" @back="goBackToPersonas" />
    <div v-else class="personas-content">
      <h1>Personas</h1>
      <div class="content-area">
        <!-- Persona list will go here -->
      </div>
      <button class="create-btn" @click="createNewPersona">
        <i class="fa-solid fa-plus"></i>
        Create New Persona
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

.personas-content {
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