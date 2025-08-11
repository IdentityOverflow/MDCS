<script setup lang="ts">
interface Persona {
  id: string
  name: string
  description: string
  model: string
  template: string
  mode: 'autonomous' | 'reactive'
  loop_frequency?: number
  first_message?: string
  image: string
}

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

function truncateDescription(description: string, maxLength: number = 100): string {
  if (description.length <= maxLength) {
    return description
  }
  return description.substring(0, maxLength).trim() + '...'
}

function getPersonaImage(imagePath: string): string {
  return imagePath || '/src/assets/persona.png'
}

function handleImageError(event: Event) {
  const img = event.target as HTMLImageElement
  if (img.src !== '/src/assets/persona.png') {
    img.src = '/src/assets/persona.png'
  }
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
  <div class="persona-card" @click="selectPersona">
    <div class="card-header">
      <h3 class="persona-name">{{ persona.name }}</h3>
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
      <div class="image-section">
        <div class="card-image">
          <img :src="getPersonaImage(persona.image)" :alt="persona.name" @error="handleImageError" />
        </div>
        <span class="persona-mode" :class="persona.mode">{{ persona.mode }}</span>
      </div>
      
      <div class="card-content">
        <p class="persona-description">{{ truncateDescription(persona.description) }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.persona-card {
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, var(--bg) 0%, var(--secondary) 100%);
  border: 1px solid var(--border);
  border-left: 3px solid var(--border);
  border-radius: 0;
  padding: 16px;
  gap: 12px;
  transition: all 0.3s ease;
  box-shadow: inset 0 0 10px rgba(0, 212, 255, 0.1);
  position: relative;
  clip-path: polygon(0 0, 108% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%);
  min-height: 120px;
  cursor: pointer;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.card-body {
  display: flex;
  gap: 16px;
  flex: 1;
}

.persona-card::before {
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

.persona-card:hover {
  border-color: var(--fg);
  border-left-color: var(--fg);
  box-shadow: 0 0 15px var(--glow);
  background: linear-gradient(135deg, var(--secondary) 0%, var(--surface) 100%);
}

.persona-card:hover::before {
  background: var(--fg);
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

.persona-name {
  color: var(--fg);
  font-size: 1.1em;
  font-weight: 600;
  margin: 0;
  word-wrap: break-word;
  flex: 1;
}

.card-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
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

.persona-description {
  color: var(--fg);
  font-size: 0.9em;
  line-height: 1.4;
  margin: 0;
  opacity: 0.8;
}

.persona-mode {
  display: inline-block;
  padding: 2px 8px;
  font-size: 0.7em;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-radius: 0;
  border: 1px solid;
}

.persona-mode.reactive {
  color: var(--fg);
  border-color: var(--border);
  background: rgba(0, 255, 255, 0.1);
}

.persona-mode.autonomous {
  color: var(--accent);
  border-color: var(--accent);
  background: rgba(255, 0, 110, 0.1);
}
</style>