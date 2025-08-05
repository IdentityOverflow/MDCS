<script setup lang="ts">
const emit = defineEmits<{
  selectComponent: [componentName: string]
}>()
</script>

<template>
  <div class="control-panel">
    <div class="button-grid">
      <button class="control-btn" @click="emit('selectComponent', 'Personas')">
        <i class="fa-solid fa-user-tie"></i>
        <span>Personas</span>
      </button>
      <button class="control-btn" @click="emit('selectComponent', 'Modules')">
        <i class="fa-solid fa-puzzle-piece"></i>
        <span>Modules</span>
      </button>
      <button class="control-btn" @click="emit('selectComponent', 'Scratchpad')">
        <i class="fa-solid fa-code"></i>
        <span>Scratchpad</span>
      </button>
      <button class="control-btn" @click="emit('selectComponent', 'Tools')">
        <i class="fa-solid fa-wrench"></i>
        <span>Tools</span>
      </button>
      <button class="control-btn" @click="emit('selectComponent', 'Files')">
        <i class="fa-solid fa-folder"></i>
        <span>Files</span>
      </button>
      <button class="control-btn" @click="emit('selectComponent', 'Settings')">
        <i class="fa-solid fa-gear"></i>
        <span>Settings</span>
      </button>
      <button class="control-btn"></button>
      <button class="control-btn"></button>
      <button class="control-btn"></button>
    </div>
  </div>
</template>

<style scoped>
.control-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 2px;
  grid-area: C;
  padding: 8px;
}

.button-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(3, 1fr);
  gap: 6px;
  height: 100%;
}

.control-btn {
  background: #B12C00;
  border: 1px solid var(--border);
  color: white;
  border-radius: 12px;
  cursor: pointer;
  font-size: 0.9em;
  font-weight: 600;
  transition: background-color 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 6px;
}

.control-btn i {
  font-size: 2em;
}

.control-btn span {
  font-size: 1em;
}

.control-btn:hover {
  background: #EB5B00;
}

.control-btn:active {
  background: #9A2400;
}
</style>