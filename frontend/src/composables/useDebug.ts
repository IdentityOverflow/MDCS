/**
 * Composable for managing debug data and records
 */

import { ref, computed, watch } from 'vue'
import { useLocalStorage } from './storage'

export interface DebugData {
  provider_request: {
    message: string
    provider_type: string
    provider_settings: Record<string, any>
    chat_controls: Record<string, any>
    system_prompt: string
  }
  provider_response: {
    content: string
    model: string
    provider_type: string
    metadata: Record<string, any>
    thinking?: string
  }
  request_timestamp: number
  response_timestamp: number
}

export interface DebugRecord {
  id: string
  timestamp: number
  persona_name?: string
  persona_id?: string
  provider: string
  model: string
  request: DebugData['provider_request']
  response: DebugData['provider_response']
  response_time: number
  resolved_system_prompt?: string
}

export interface DebugSettings {
  maxRecords: number
  enabled: boolean
}

const DEFAULT_SETTINGS: DebugSettings = {
  maxRecords: 10,
  enabled: true
}

// Global state for debug records
const debugRecords = ref<DebugRecord[]>([])

// Settings with localStorage persistence
const { data: debugSettings, save: saveSettings } = useLocalStorage({
  key: 'debug-settings',
  defaultValue: DEFAULT_SETTINGS
})

// Load saved debug records from localStorage on initialization
const loadDebugRecords = () => {
  const saved = localStorage.getItem('debug-records')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      if (Array.isArray(parsed)) {
        debugRecords.value = parsed
      }
    } catch (error) {
      console.warn('Failed to load debug records from localStorage:', error)
      debugRecords.value = []
    }
  }
}

// Save debug records to localStorage
const saveDebugRecords = () => {
  try {
    localStorage.setItem('debug-records', JSON.stringify(debugRecords.value))
  } catch (error) {
    console.warn('Failed to save debug records to localStorage:', error)
  }
}

// Watch for changes and auto-save
watch(debugRecords, saveDebugRecords, { deep: true })

// Load records on first use
loadDebugRecords()

export function useDebug() {
  /**
   * Add a new debug record
   */
  const addDebugRecord = (data: {
    debugData: DebugData
    personaName?: string
    personaId?: string
    resolvedSystemPrompt?: string
    responseTime?: number
  }) => {
    if (!debugSettings.value.enabled) {
      return
    }

    const record: DebugRecord = {
      id: crypto.randomUUID(),
      timestamp: Date.now(),
      persona_name: data.personaName,
      persona_id: data.personaId,
      provider: data.debugData.provider_response.provider_type,
      model: data.debugData.provider_response.model,
      request: data.debugData.provider_request,
      response: data.debugData.provider_response,
      response_time: data.responseTime || (data.debugData.response_timestamp - data.debugData.request_timestamp),
      resolved_system_prompt: data.resolvedSystemPrompt
    }

    // Add to beginning of array
    debugRecords.value.unshift(record)

    // Trim to max records (FIFO)
    if (debugRecords.value.length > debugSettings.value.maxRecords) {
      debugRecords.value = debugRecords.value.slice(0, debugSettings.value.maxRecords)
    }
  }

  /**
   * Clear all debug records
   */
  const clearDebugRecords = () => {
    debugRecords.value = []
  }

  /**
   * Remove a specific debug record
   */
  const removeDebugRecord = (id: string) => {
    const index = debugRecords.value.findIndex(record => record.id === id)
    if (index !== -1) {
      debugRecords.value.splice(index, 1)
    }
  }

  /**
   * Update debug settings
   */
  const updateSettings = (newSettings: Partial<DebugSettings>) => {
    Object.assign(debugSettings.value, newSettings)
    saveSettings()

    // If max records was reduced, trim the array
    if (newSettings.maxRecords && debugRecords.value.length > newSettings.maxRecords) {
      debugRecords.value = debugRecords.value.slice(0, newSettings.maxRecords)
    }
  }

  /**
   * Get records sorted by timestamp (newest first)
   */
  const sortedRecords = computed(() => {
    return [...debugRecords.value].sort((a, b) => b.timestamp - a.timestamp)
  })

  /**
   * Get records count
   */
  const recordsCount = computed(() => debugRecords.value.length)

  /**
   * Check if records are at max capacity
   */
  const isAtMaxCapacity = computed(() => 
    debugRecords.value.length >= debugSettings.value.maxRecords
  )

  return {
    // State
    debugRecords: sortedRecords,
    debugSettings,
    recordsCount,
    isAtMaxCapacity,

    // Actions
    addDebugRecord,
    clearDebugRecords,
    removeDebugRecord,
    updateSettings
  }
}