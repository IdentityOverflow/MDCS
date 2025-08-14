<script setup lang="ts">
import { ref } from 'vue'
import OllamaConnection from '../connections/OllamaConnection.vue'
import OpenAIConnection from '../connections/OpenAIConnection.vue'
import DatabaseConnection from '../connections/DatabaseConnection.vue'

type SettingsView = 'main' | 'ollama' | 'openai' | 'database'

const currentView = ref<SettingsView>('main')

function showConnectionForm(type: SettingsView) {
  currentView.value = type
}

function goBack() {
  currentView.value = 'main'
}
</script>

<template>
  <div class="settings-container">
    <!-- Main Settings Menu -->
    <div v-if="currentView === 'main'" class="settings-main">
      <h1 class="settings-title">Settings</h1>
      
      <div class="settings-grid">
        <button class="cyberpunk-btn" @click="showConnectionForm('ollama')">
          <i class="fa-solid fa-server"></i>
          <span>Ollama Connection</span>
        </button>
        
        <button class="cyberpunk-btn" @click="showConnectionForm('openai')">
          <i class="fa-solid fa-brain"></i>
          <span>OpenAI API</span>
        </button>
        
        <button class="cyberpunk-btn" @click="showConnectionForm('database')">
          <i class="fa-solid fa-database"></i>
          <span>Database</span>
        </button>
        
        <button class="cyberpunk-btn" disabled>
          <i class="fa-solid fa-palette"></i>
          <span>Theme</span>
        </button>
        
        <button class="cyberpunk-btn" disabled>
          <i class="fa-solid fa-bell"></i>
          <span>Notifications</span>
        </button>
        
        <button class="cyberpunk-btn" disabled>
          <i class="fa-solid fa-shield"></i>
          <span>Security</span>
        </button>
      </div>
    </div>

    <!-- Connection Forms -->
    <div v-else class="form-container">
      <div class="form-header">
        <button class="action-btn form-back-btn" @click="goBack">
          <i class="fa-solid fa-arrow-left"></i>
          Back
        </button>
        <h1 class="form-title" v-if="currentView === 'ollama'">Ollama Connection</h1>
        <h1 class="form-title" v-if="currentView === 'openai'">OpenAI API Connection</h1>
        <h1 class="form-title" v-if="currentView === 'database'">Database Connection</h1>
      </div>
      
      <div class="form-content-area">
        <OllamaConnection v-if="currentView === 'ollama'" />
        <OpenAIConnection v-if="currentView === 'openai'" />
        <DatabaseConnection v-if="currentView === 'database'" />
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';
@import '@/assets/form.css';
@import '@/assets/cyberpunk-buttons.css';

.settings-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--surface);
}

/* Main Settings Menu */
.settings-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
}

.settings-title {
  color: var(--fg);
  font-size: 1.6em;
  font-weight: 600;
  margin-bottom: 48px;
  text-align: center;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 24px;
  max-width: 600px;
  width: 100%;
}


</style>