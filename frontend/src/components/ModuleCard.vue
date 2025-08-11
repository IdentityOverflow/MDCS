<script setup lang="ts">
interface Module {
  id: string
  name: string
  description: string
  content: string
  type: 'simple' | 'advanced'
  trigger_pattern?: string
  script?: string
  timing?: 'before' | 'after' | 'custom'
}

const props = defineProps<{
  module: Module
}>()

const emit = defineEmits<{
  edit: [id: string]
  delete: [id: string]
}>()

function handleEdit() {
  emit('edit', props.module.id)
}

function handleDelete() {
  emit('delete', props.module.id)
}
</script>

<template>
  <div class="module-card">
    <div class="card-header">
      <div class="module-info">
        <h3 class="module-name">{{ module.name }}</h3>
        <span class="module-type" :class="module.type">{{ module.type }}</span>
      </div>
      <div class="card-actions">
        <button class="icon-btn edit-btn" @click="handleEdit" title="Edit">
          <i class="fa-solid fa-edit"></i>
        </button>
        <button class="icon-btn delete-btn" @click="handleDelete" title="Delete">
          <i class="fa-solid fa-trash"></i>
        </button>
      </div>
    </div>
    
    <div class="card-body">
      <p class="module-description">{{ module.description }}</p>
      
      <div v-if="module.type === 'advanced'" class="advanced-info">
        <div class="info-row">
          <span class="info-label">Timing:</span>
          <span class="info-value">{{ module.timing }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Trigger:</span>
          <span class="info-value">{{ module.trigger_pattern || 'None' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.module-card {
  background: linear-gradient(135deg, var(--bg) 0%, var(--secondary) 100%);
  border: 1px solid var(--border);
  border-left: 3px solid var(--border);
  border-radius: 0;
  padding: 16px;
  transition: all 0.3s ease;
  box-shadow: inset 0 0 10px rgba(0, 212, 255, 0.1);
  position: relative;
  clip-path: polygon(0 0, 108% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%);
}

.module-card::before {
  content: '';
  position: absolute;
  bottom: 8px;
  right: 0;
  width: 16px;
  height: 1px;
  background: var(--border);
  transform: rotate(-45deg);
  transform-origin: right center;
  transition: all 0.3s ease;
}

.module-card:hover {
  border-color: var(--fg);
  border-left-color: var(--fg);
  box-shadow: 0 0 15px var(--glow);
  background: linear-gradient(135deg, var(--secondary) 0%, var(--surface) 100%);
}

.module-card:hover::before {
  background: var(--fg);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.module-info {
  flex: 1;
  min-width: 0;
}

.module-name {
  color: var(--fg);
  font-size: 1.1em;
  font-weight: 600;
  margin: 0 0 4px 0;
  word-wrap: break-word;
}

.module-type {
  display: inline-block;
  padding: 2px 8px;
  font-size: 0.7em;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-radius: 0;
  border: 1px solid;
}

.module-type.simple {
  color: var(--fg);
  border-color: var(--border);
  background: rgba(0, 255, 255, 0.1);
}

.module-type.advanced {
  color: var(--accent);
  border-color: var(--accent);
  background: rgba(255, 0, 110, 0.1);
}

.card-actions {
  display: flex;
  gap: 4px;
  margin-left: 8px;
}

.icon-btn {
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--fg);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-size: 0.8em;
}

.icon-btn:hover {
  background: var(--surface);
  border-color: var(--fg);
  box-shadow: 0 0 5px var(--glow);
}

.edit-btn:hover {
  color: var(--border);
}

.delete-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.module-description {
  color: var(--fg);
  font-size: 0.9em;
  line-height: 1.4;
  margin: 0;
  opacity: 0.8;
}

.advanced-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  background: rgba(255, 0, 110, 0.05);
  border: 1px dashed var(--accent);
  border-radius: 0;
}

.info-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.info-label {
  color: var(--accent);
  font-size: 0.75em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  min-width: 60px;
}

.info-value {
  color: var(--fg);
  font-size: 0.8em;
  font-weight: 500;
  opacity: 0.9;
  word-break: break-all;
}
</style>