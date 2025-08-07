<script setup lang="ts">
import { ref } from 'vue'
import MainChat from '../components/MainChat.vue'
import DisplayArea from '../components/DisplayArea.vue'
import ControlPanel from '../components/ControlPanel.vue'
import Info from '../components/Info.vue'

const selectedComponent = ref('Personas')

function handleComponentSelect(componentName: string) {
  selectedComponent.value = componentName
}
</script>

<template>
  <div class="container">
    <MainChat />
    <DisplayArea :selected-component="selectedComponent" />
    <ControlPanel @select-component="handleComponentSelect" />
    <Info />
  </div>
</template>

<style scoped>
.container {
  display: grid;
  width: 100%;
  height: 100%;
  grid-template-columns: var(--col1) var(--col2) var(--col3) var(--col4);
  grid-template-rows: var(--col1) var(--col2) var(--col3) var(--col4);
  grid-template-areas:
    "A B B B"
    "A F F C"
    "A F F C"
    "A F F C";
}
</style>
