<script setup lang="ts">
import { ref } from 'vue'

// Empty rooms for now - will be implemented later with Discord/Matrix-like functionality
const rooms = ref([])
</script>

<template>
  <div class="view-container">
    <div class="rooms-content">
      <div class="header">
        <h1>Chat Rooms</h1>
      </div>
      
      <div class="content-area">
        <!-- Empty State -->
        <div class="empty-container">
          <div class="empty-text">
            <i class="fa-solid fa-door-open"></i>
            <h3>No rooms yet</h3>
            <p>Room functionality will be implemented later with Discord/Matrix-like features</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';
@import '@/assets/empty-states.css';

.view-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.rooms-content {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.header {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 24px;
}

h1 {
  color: var(--fg);
  font-size: 1.6em;
  font-weight: 600;
  margin: 0;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}


/* Empty state */
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  text-align: center;
}

.empty-text i {
  font-size: 3em;
  color: var(--accent);
  opacity: 0.5;
  margin-bottom: 16px;
}

.empty-text h3 {
  color: var(--fg);
  margin: 0 0 8px 0;
  font-weight: 500;
}

.empty-text p {
  color: var(--fg-secondary);
  margin: 0;
  font-size: 0.9em;
  opacity: 0.8;
}
</style>