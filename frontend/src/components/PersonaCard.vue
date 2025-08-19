<script setup lang="ts">
import type { Persona } from '@/types'
import { truncateDescription, getPersonaImage, handleImageError } from '@/composables/utils'

const props = defineProps<{
  persona: Persona
}>()

const emit = defineEmits<{
  select: [persona: Persona]
  edit: [id: string]
  delete: [id: string]
}>()

function selectPersona() {
  emit('select', props.persona)
}

function handleEdit(event: Event) {
  event.stopPropagation() // Prevent card selection when clicking edit
  emit('edit', props.persona.id)
}

function handleDelete(event: Event) {
  event.stopPropagation() // Prevent card selection when clicking delete
  emit('delete', props.persona.id)
}
</script>

<template>
  <div class="card-base clickable" @click="selectPersona">
    <div class="card-header">
      <h3 class="card-title">{{ persona.name }}</h3>
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
      <div class="image-section">
        <div class="card-image">
          <img :src="getPersonaImage(persona.image_path)" :alt="persona.name" @error="handleImageError" />
        </div>
        <span class="card-badge" :class="persona.mode === 'autonomous' ? 'accent' : 'primary'">{{ persona.mode }}</span>
      </div>
      
      <div class="card-content">
        <p class="card-description">{{ truncateDescription(persona.description) }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/card.css';

/* Persona-specific layout */
.card-base {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-body {
  display: flex;
  gap: 16px;
  flex: 1;
}

.image-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  align-self: center;
}

.card-image {
  flex-shrink: 0;
  width: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface);
  border: 1px solid var(--border);
  clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%);
  aspect-ratio: 1;
}

.card-image img {
  width: 70px;
  height: 70px;
  object-fit: cover;
  filter: drop-shadow(0 0 5px rgba(0, 212, 255, 0.3));
}

.card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}
</style>