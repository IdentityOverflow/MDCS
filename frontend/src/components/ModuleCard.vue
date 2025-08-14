<script setup lang="ts">
import type { Module } from '@/types'

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
  <div class="card-base">
    <div class="card-header">
      <div class="module-info">
        <h3 class="card-title">{{ module.name }}</h3>
        <span class="card-badge" :class="module.type === 'advanced' ? 'accent' : 'primary'">{{ module.type }}</span>
      </div>
      <div class="card-actions">
        <button class="card-icon-btn edit-btn" @click="handleEdit" title="Edit">
          <i class="fa-solid fa-edit"></i>
        </button>
        <button class="card-icon-btn delete-btn" @click="handleDelete" title="Delete">
          <i class="fa-solid fa-trash"></i>
        </button>
      </div>
    </div>
    
    <div class="card-body">
      <p class="card-description">{{ module.description }}</p>
      
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
@import '@/assets/card.css';

.module-info {
  flex: 1;
  min-width: 0;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-actions {
  margin-left: 8px;
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