<script setup lang="ts">
const emit = defineEmits<{
  selectComponent: [componentName: string]
}>()

const openScriptingDocs = () => {
  window.open('/docs/scripting', '_blank')
}
</script>

<template>
  <div class="control-panel">
    <div class="button-grid">
      <button class="cyberpunk-btn small" @click="emit('selectComponent', 'Personas')">
        <i class="fa-solid fa-user-tie"></i>
        <span>Personas</span>
      </button>
      <button class="cyberpunk-btn small" @click="emit('selectComponent', 'Modules')">
        <i class="fa-solid fa-puzzle-piece"></i>
        <span>Modules</span>
      </button>
      <button class="cyberpunk-btn small" @click="emit('selectComponent', 'Scratchpad')">
        <i class="fa-solid fa-file"></i>
        <span>Scratchpad</span>
      </button>
      <button class="cyberpunk-btn small" @click="emit('selectComponent', 'Tools')">
        <i class="fa-solid fa-wrench"></i>
        <span>Tools</span>
      </button>
      <button class="cyberpunk-btn small" @click="emit('selectComponent', 'Files')">
        <i class="fa-solid fa-folder"></i>
        <span>Files</span>
      </button>
      <button class="cyberpunk-btn small" @click="emit('selectComponent', 'Rooms')">
        <i class="fa-solid fa-door-open"></i>
        <span>Rooms</span>
      </button>
      <button class="cyberpunk-btn small" @click="emit('selectComponent', 'Settings')">
        <i class="fa-solid fa-gear"></i>
        <span>Settings</span>
      </button>
      <button class="cyberpunk-btn small" @click="emit('selectComponent', 'Debug')">
        <i class="fa-solid fa-bug"></i>
        <span>Debug</span>
      </button>
      <button class="cyberpunk-btn small" @click="openScriptingDocs">
        <i class="fa-solid fa-code"></i>
        <span>Scripting</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/cyberpunk-buttons.css';

.control-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 2px;
  grid-area: C;
  padding: 8px;
  overflow: hidden;
  box-sizing: border-box;
}

.button-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(3, 1fr);
  gap: 6px;
  height: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

/* Additional specific styling if needed */
</style>