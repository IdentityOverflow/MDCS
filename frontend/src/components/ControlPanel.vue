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

.control-btn {
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
  border: 1px solid #00d4ff;
  border-bottom-right-radius: 0;
  color: #00ffff;
  cursor: pointer;
  font-size: 0.9em;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 6px;
  box-shadow: inset 0 0 10px rgba(0, 212, 255, 0.1);
  position: relative;
  overflow: hidden;
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%);
  box-sizing: border-box;
}

.control-btn::before {
  content: '';
  position: absolute;
  bottom: 9px;
  right: 0;
  width: 17px;
  height: 1px;
  background: #00d4ff;
  transform: rotate(-45deg);
  transform-origin: right center;
}

.control-btn::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.2), transparent);
  transition: left 0.6s;
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%);
  pointer-events: none;
  z-index: -1;
}

.control-btn i {
  font-size: 2em;
}

.control-btn span {
  font-size: 1em;
}


.control-btn:hover {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border-color: #00ffff;
  color: #ffffff;
  box-shadow: inset 0 0 15px rgba(0, 212, 255, 0.4), inset 0 0 5px rgba(0, 255, 255, 0.6);
  transform: translateY(-1px);
}

.control-btn:hover::before {
  background: #00ffff;
}

.control-btn:hover::after {
  left: 100%;
}


.control-btn:active {
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
  transform: translateY(0);
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.3), inset 0 0 20px rgba(0, 212, 255, 0.3);
}
</style>