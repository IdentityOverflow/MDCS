<script setup lang="ts">
import { ref } from 'vue'
import NewPersona from './NewPersona.vue'
import PersonaCard from '../PersonaCard.vue'

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

const showNewPersona = ref(false)

const emit = defineEmits<{
  selectPersona: [persona: Persona]
}>()

// Dummy personas for testing
const personas = ref<Persona[]>([
  {
    id: 'persona_1',
    name: 'Data Analyst',
    description: 'Specialized in analyzing complex datasets and providing insights through statistical analysis and data visualization.Specialized in analyzing complex datasets and providing insights through statistical analysis and data visualization.Specialized in analyzing complex datasets and providing insights through statistical analysis and data visualization.Specialized in analyzing complex datasets and providing insights through statistical analysis and data visualization.Specialized in analyzing complex datasets and providing insights through statistical analysis and data visualization.Specialized in analyzing complex datasets and providing insights through statistical analysis and data visualization.Specialized in analyzing complex datasets and providing insights through statistical analysis and data visualization.',
    model: 'claude-3-sonnet',
    template: 'You are an expert data analyst with advanced skills in statistics, data mining, and visualization. Use {data_validator_module} and {chart_generator_module} for your analysis.',
    mode: 'reactive',
    image: '/src/assets/tux.png'
  },
  {
    id: 'persona_2',
    name: 'Code Reviewer',
    description: 'Autonomous code quality inspector that continuously monitors repositories for best practices and security issues.',
    model: 'gpt-4',
    template: 'You are a senior software engineer focused on code quality, security, and best practices. Utilize {lint_module}, {security_scanner_module}, and {code_formatter_module} for comprehensive reviews.',
    mode: 'autonomous',
    loop_frequency: 2.5,
    image: '/src/assets/RPG.png'
  },
  {
    id: 'persona_3',
    name: 'Creative Writer Assistant',
    description: 'Helps generate creative content including stories, marketing copy, and engaging social media posts.',
    model: 'claude-3-opus',
    template: 'You are a creative writer with expertise in storytelling, marketing, and content creation.',
    mode: 'reactive',
    first_message: 'Hello! I\'m ready to help you create amazing content.',
    image: '/src/assets/its-fine-im-fine.gif'
  },
  {
    id: 'persona_4',
    name: 'System Monitor',
    description: 'Continuously monitors system performance, resource usage, and alerts administrators of potential issues.',
    model: 'gpt-3.5-turbo',
    template: 'You are a system administrator with deep knowledge of server monitoring and performance optimization.',
    mode: 'autonomous',
    loop_frequency: 10.0,
    image: '/src/assets/persona.png'
  },
  {
    id: 'persona_5',
    name: 'Research Assistant',
    description: 'Conducts thorough research on various topics and summarizes findings in clear, actionable reports.',
    model: 'claude-3-sonnet',
    template: 'You are a research assistant with excellent analytical and summarization skills.',
    mode: 'reactive',
    image: '/src/assets/tuxs.png'
  },
  {
    id: 'persona_6',
    name: 'Chat Moderator',
    description: 'Autonomous moderator that maintains community guidelines and ensures positive interactions in chat channels.',
    model: 'gpt-4',
    template: 'You are a community moderator focused on maintaining positive and respectful communication.',
    mode: 'autonomous',
    loop_frequency: 1.0,
    image: '/src/assets/tux.png'
  }
])

function createNewPersona() {
  showNewPersona.value = true
}

function goBackToPersonas() {
  showNewPersona.value = false
}

function handlePersonaSelect(persona: Persona) {
  emit('selectPersona', persona)
}

function editPersona(id: string) {
  console.log('Edit persona:', id)
}

function deletePersona(id: string) {
  console.log('Delete persona:', id)
}
</script>

<template>
  <div class="view-container">
    <NewPersona v-if="showNewPersona" @back="goBackToPersonas" />
    <div v-else class="personas-content">
      <div class="header">
        <h1>Personas</h1>
        <button class="action-btn new-btn" @click="createNewPersona">
          <i class="fa-solid fa-plus"></i>
          New
        </button>
      </div>
      <div class="content-area">
        <div class="personas-grid">
          <PersonaCard
            v-for="persona in personas"
            :key="persona.id"
            :persona="persona"
            @select="handlePersonaSelect"
            @edit="editPersona"
            @delete="deletePersona"
          />
        </div>
      </div>
      
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/buttons.css';

.view-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.personas-content {
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
  margin-bottom: 16px;
  position: relative;
}

h1 {
  color: var(--fg);
  font-size: 1.6em;
  font-weight: 600;
  margin: 0;
}

.new-btn {
  position: absolute;
  right: 0;
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.personas-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 0 4px;
}

</style>