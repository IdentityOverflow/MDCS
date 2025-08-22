<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import { useModules } from '@/composables/useModules'

const props = defineProps<{
  modelValue: string
  placeholder?: string
  rows?: number
  invalid?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'input': []
}>()

// Template content
const content = ref(props.modelValue || '')

// Textarea reference
const textarea = ref<HTMLTextAreaElement>()

// Autocomplete state
const showAutocomplete = ref(false)
const autocompleteOptions = ref<Array<{ name: string; description?: string }>>([])
const selectedOptionIndex = ref(0)
const autocompletePosition = ref({ top: 0, left: 0 })
const currentModuleSearch = ref('')

// Use modules composable
const { modules, fetchModules, activeModules } = useModules()

// Load modules on mount
onMounted(async () => {
  await fetchModules()
})

// Watch for prop changes
watch(() => props.modelValue, (newValue) => {
  content.value = newValue || ''
})

// Watch content changes
watch(content, (newValue) => {
  emit('update:modelValue', newValue)
  emit('input')
})

// Computed filtered modules for autocomplete
const filteredModules = computed(() => {
  if (!currentModuleSearch.value) {
    return activeModules.value.map(module => ({
      name: module.name,
      description: module.description
    }))
  }
  
  const search = currentModuleSearch.value.toLowerCase()
  return activeModules.value
    .filter(module => module.name.toLowerCase().includes(search))
    .map(module => ({
      name: module.name,
      description: module.description
    }))
})

// Handle textarea input
function handleInput(event: Event) {
  const target = event.target as HTMLTextAreaElement
  content.value = target.value
  checkForModuleReference()
}

// Check for @module reference at cursor
function checkForModuleReference() {
  if (!textarea.value) return
  
  const cursorPosition = textarea.value.selectionStart
  const text = content.value.substring(0, cursorPosition)
  
  // Find the last @ symbol before cursor
  const lastAtIndex = text.lastIndexOf('@')
  
  if (lastAtIndex === -1) {
    hideAutocomplete()
    return
  }
  
  // Check if this @ is escaped (preceded by \)
  const charBeforeAt = lastAtIndex > 0 ? text[lastAtIndex - 1] : ''
  if (charBeforeAt === '\\') {
    hideAutocomplete()
    return
  }
  
  // Check if there's a space or special character after @
  const afterAt = text.substring(lastAtIndex + 1)
  const hasSpaceOrSpecial = /[\s\n\r\t]/.test(afterAt)
  
  if (hasSpaceOrSpecial) {
    hideAutocomplete()
    return
  }
  
  // Extract the partial module name
  const moduleNameMatch = afterAt.match(/^([a-z0-9_]*)$/)
  
  if (moduleNameMatch) {
    currentModuleSearch.value = moduleNameMatch[1]
    showAutocompleteAtCursor()
  } else {
    hideAutocomplete()
  }
}

// Show autocomplete dropdown at cursor position
function showAutocompleteAtCursor() {
  if (!textarea.value) return
  
  const cursorPosition = textarea.value.selectionStart
  const textBeforeCursor = content.value.substring(0, cursorPosition)
  
  // Calculate approximate position (basic implementation)
  const lines = textBeforeCursor.split('\n')
  const currentLine = lines.length - 1
  const currentColumn = lines[lines.length - 1].length
  
  // Approximate character width and line height
  const charWidth = 8
  const lineHeight = 20
  
  autocompletePosition.value = {
    top: (currentLine + 1) * lineHeight + 4,
    left: currentColumn * charWidth
  }
  
  autocompleteOptions.value = filteredModules.value
  selectedOptionIndex.value = 0
  showAutocomplete.value = autocompleteOptions.value.length > 0
}

// Hide autocomplete
function hideAutocomplete() {
  showAutocomplete.value = false
  currentModuleSearch.value = ''
  selectedOptionIndex.value = 0
}

// Handle keydown events
function handleKeydown(event: KeyboardEvent) {
  if (!showAutocomplete.value) return
  
  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      selectedOptionIndex.value = Math.min(
        selectedOptionIndex.value + 1,
        autocompleteOptions.value.length - 1
      )
      break
      
    case 'ArrowUp':
      event.preventDefault()
      selectedOptionIndex.value = Math.max(selectedOptionIndex.value - 1, 0)
      break
      
    case 'Tab':
    case 'Enter':
      event.preventDefault()
      selectCurrentOption()
      break
      
    case 'Escape':
      event.preventDefault()
      hideAutocomplete()
      break
  }
}

// Select the currently highlighted option
function selectCurrentOption() {
  if (!showAutocomplete.value || !textarea.value) return
  
  const selectedModule = autocompleteOptions.value[selectedOptionIndex.value]
  if (!selectedModule) return
  
  const cursorPosition = textarea.value.selectionStart
  const text = content.value
  
  // Find the @ symbol before cursor
  const textBeforeCursor = text.substring(0, cursorPosition)
  const lastAtIndex = textBeforeCursor.lastIndexOf('@')
  
  if (lastAtIndex === -1) return
  
  // Replace from @ to cursor with the selected module name
  const beforeAt = text.substring(0, lastAtIndex)
  const afterCursor = text.substring(cursorPosition)
  const newContent = beforeAt + `@${selectedModule.name}` + afterCursor
  
  content.value = newContent
  
  // Set cursor position after the inserted module name
  nextTick(() => {
    if (textarea.value) {
      const newCursorPos = lastAtIndex + selectedModule.name.length + 1
      textarea.value.setSelectionRange(newCursorPos, newCursorPos)
      textarea.value.focus()
    }
  })
  
  hideAutocomplete()
}

// Select option by clicking
function selectOption(index: number) {
  selectedOptionIndex.value = index
  selectCurrentOption()
}

// Handle clicks outside to hide autocomplete
function handleClickOutside(event: Event) {
  const target = event.target as HTMLElement
  if (!target.closest('.template-editor')) {
    hideAutocomplete()
  }
}

// Add click outside listener
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

// Cleanup
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="template-editor">
    <div class="editor-container">
      <textarea
        ref="textarea"
        v-model="content"
        :placeholder="placeholder"
        :rows="rows || 8"
        :class="['template-textarea', { 'invalid': invalid }]"
        @input="handleInput"
        @keydown="handleKeydown"
        @click="checkForModuleReference"
        @keyup="checkForModuleReference"
      ></textarea>
      
      <!-- Autocomplete Dropdown -->
      <div 
        v-if="showAutocomplete" 
        class="autocomplete-dropdown"
        :style="{
          top: `${autocompletePosition.top}px`,
          left: `${autocompletePosition.left}px`
        }"
      >
        <div class="autocomplete-header">
          <i class="fa-solid fa-puzzle-piece"></i>
          Available Modules
        </div>
        <div 
          v-for="(option, index) in autocompleteOptions"
          :key="option.name"
          :class="['autocomplete-option', { 'selected': index === selectedOptionIndex }]"
          @click="selectOption(index)"
        >
          <div class="option-name">@{{ option.name }}</div>
          <div v-if="option.description" class="option-description">
            {{ option.description }}
          </div>
        </div>
        <div v-if="autocompleteOptions.length === 0" class="no-options">
          No matching modules found
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.template-editor {
  position: relative;
  width: 100%;
}

.editor-container {
  position: relative;
}

.template-textarea {
  width: 100%;
  min-height: 120px;
  padding: 12px;
  background: var(--surface);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 2px;
  color: var(--fg);
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
  line-height: 1.4;
  resize: vertical;
  outline: none;
  transition: all 0.2s ease;
}

.template-textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.1);
}

.template-textarea.invalid {
  border-color: #ff4757;
  box-shadow: 0 0 0 2px rgba(255, 71, 87, 0.2);
}

.template-textarea::placeholder {
  color: var(--fg);
  opacity: 0.5;
}

/* Autocomplete Dropdown */
.autocomplete-dropdown {
  position: absolute;
  z-index: 1000;
  background: var(--surface);
  border: 1px solid var(--accent);
  border-radius: 2px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  max-height: 200px;
  overflow-y: auto;
  min-width: 250px;
  font-size: 0.85em;
}

.autocomplete-header {
  padding: 8px 12px;
  background: rgba(0, 212, 255, 0.1);
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  color: var(--accent);
  font-weight: 600;
  font-size: 0.8em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.autocomplete-option {
  padding: 8px 12px;
  cursor: pointer;
  transition: background-color 0.15s ease;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.autocomplete-option:hover,
.autocomplete-option.selected {
  background: rgba(0, 212, 255, 0.1);
}

.autocomplete-option:last-child {
  border-bottom: none;
}

.option-name {
  font-weight: 600;
  color: var(--accent);
  font-family: 'Fira Code', monospace;
}

.option-description {
  font-size: 0.8em;
  color: var(--fg);
  opacity: 0.7;
  margin-top: 2px;
  line-height: 1.3;
}

.no-options {
  padding: 12px;
  text-align: center;
  color: var(--fg);
  opacity: 0.6;
  font-style: italic;
}

/* Scrollbar for autocomplete */
.autocomplete-dropdown::-webkit-scrollbar {
  width: 6px;
}

.autocomplete-dropdown::-webkit-scrollbar-track {
  background: var(--bg-2);
}

.autocomplete-dropdown::-webkit-scrollbar-thumb {
  background: var(--accent);
  border-radius: 3px;
}

.autocomplete-dropdown::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 212, 255, 0.8);
}
</style>