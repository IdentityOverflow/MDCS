<script setup lang="ts">
import { computed } from 'vue'
import Personas from './views/Personas.vue'
import Modules from './views/Modules.vue'
import Scratchpad from './views/Scratchpad.vue'
import Tools from './views/Tools.vue'
import Files from './views/Files.vue'
import Settings from './views/Settings.vue'

const props = defineProps<{
  selectedComponent: string
}>()

const currentComponent = computed(() => {
  switch (props.selectedComponent) {
    case 'Personas': return Personas
    case 'Modules': return Modules
    case 'Scratchpad': return Scratchpad
    case 'Tools': return Tools
    case 'Files': return Files
    case 'Settings': return Settings
    default: return Personas
  }
})
</script>

<template>
  <div class="display-area">
    <component :is="currentComponent" />
  </div>
</template>

<style scoped>
.display-area {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 2px;
  grid-area: B;
}
</style>