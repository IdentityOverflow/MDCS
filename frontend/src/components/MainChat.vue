<script setup lang="ts">
import { ref, nextTick } from 'vue'
import ChatControls from './connections/ChatControls.vue'

const message = ref('')
const showSliders = ref(false)
const textareaRef = ref<HTMLTextAreaElement>()

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

function sendMessage() {
  if (message.value.trim()) {
    console.log('Sending message:', message.value)
    // Here you would typically send the message to your chat service
    message.value = ''
    // Reset textarea height after sending
    nextTick(() => {
      autoResize()
    })
  }
}

function toggleSliders() {
  showSliders.value = !showSliders.value
}

function autoResize() {
  const textarea = textareaRef.value
  if (textarea) {
    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto'
    // Set height to scrollHeight, but respect min/max constraints
    const newHeight = Math.min(Math.max(textarea.scrollHeight, 40), 120)
    textarea.style.height = `${newHeight}px`
  }
}
</script>

<template>
  <div class="main-chat">
    <!-- Chat messages area -->
    <div class="chat-content">
      <div class="chat-messages">
        <!-- Chat messages would go here -->
        <div class="placeholder-text">Start a conversation...</div>
      </div>
    </div>
    
    <!-- Floating input container -->
    <div class="floating-input-container">
      <div class="input-card">
        <!-- Chat Controls panel (appears above input when active) -->
        <div v-if="showSliders" class="chat-controls-panel">
          <div class="controls-header">
            <h3>Chat Controls</h3>
            <button class="close-btn" @click="toggleSliders">
              <i class="fa-solid fa-times"></i>
            </button>
          </div>
          <div class="controls-content">
            <ChatControls />
          </div>
        </div>
        
        <!-- Input row -->
        <div class="input-row">
          <div class="left-controls">
            <button 
              class="icon-btn settings-btn" 
              @click="toggleSliders" 
              :class="{ active: showSliders }" 
              title="Settings"
            >
              <i class="fa-solid fa-sliders"></i>
            </button>
          </div>
          
          <div class="input-container">
            <textarea
              v-model="message"
              @keydown="handleKeydown"
              @input="autoResize"
              placeholder="Use Shift+Enter for multi-line..."
              class="chat-input"
              ref="textareaRef"
              rows="1"
            ></textarea>
          </div>
          
          <div class="right-controls">
            <button 
              class="icon-btn send-btn" 
              @click="sendMessage" 
              :disabled="!message.trim()" 
              title="Send Message"
            >
              <i class="fa-solid fa-paper-plane"></i>
            </button>
          </div>
        </div>
      </div>
      
    </div>
  </div>
</template>

<style scoped>
.main-chat {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 2px;
  grid-area: A;
  position: relative;
  overflow: hidden;
}

.chat-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  padding: 32px 16px 120px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-text {
  color: var(--fg);
  opacity: 0.4;
  font-size: 1.1em;
  font-weight: 300;
}

/* Floating input container */
.floating-input-container {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 48px);
  max-width: 600px;
  z-index: 10;
}

.input-card {
  background: linear-gradient(135deg, var(--bg) 0%, var(--secondary) 100%);
  border: 1px solid var(--border);
  border-radius: 0;
  box-shadow: 
    0 0 20px rgba(0, 212, 255, 0.2),
    inset 0 0 10px rgba(0, 212, 255, 0.1);
  clip-path: polygon(0 0, 108% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%);
  position: relative;
}

.input-card::before {
  content: '';
  position: absolute;
  bottom: 6px;
  right: 0;
  width: 12px;
  height: 1px;
  background: var(--border);
  transform: rotate(-45deg);
  transform-origin: right center;
}

/* Chat Controls panel */
.chat-controls-panel {
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  max-height: 60vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.controls-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg);
}

.controls-header h3 {
  color: var(--fg);
  font-size: 1em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  color: var(--fg);
  cursor: pointer;
  font-size: 1.2em;
  opacity: 0.7;
  transition: opacity 0.2s ease;
  padding: 4px;
}

.close-btn:hover {
  opacity: 1;
  color: var(--accent);
}

.controls-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

/* Input row */
.input-row {
  display: flex;
  align-items: flex-end;
  padding: 12px;
  gap: 8px;
}

.left-controls,
.right-controls {
  display: flex;
  gap: 6px;
}

.input-container {
  flex: 1;
}

.chat-input {
  width: 100%;
  background: transparent;
  border: none;
  color: var(--fg);
  padding: 8px 12px;
  font-size: 0.95em;
  font-weight: 400;
  font-family: inherit;
  resize: none;
  height: 40px;
  min-height: 40px;
  max-height: 120px;
  line-height: 1.4;
  overflow-y: hidden;
  transition: height 0.1s ease;
}

.chat-input:focus {
  outline: none;
}

.chat-input::placeholder {
  color: var(--fg);
  opacity: 0.4;
}

/* Icon buttons */
.icon-btn {
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--fg);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-size: 0.85em;
  opacity: 0.7;
  clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%);
}

.icon-btn:hover:not(:disabled) {
  opacity: 1;
  background: rgba(0, 212, 255, 0.1);
  border-color: var(--fg);
}

.icon-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.icon-btn.active {
  background: rgba(0, 212, 255, 0.2);
  border-color: var(--fg);
  opacity: 1;
}

.send-btn:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
}

.send-btn:not(:disabled) {
  opacity: 1;
}

</style>