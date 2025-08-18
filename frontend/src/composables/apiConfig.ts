/**
 * API Configuration Management
 * Handles backend URL configuration with localStorage persistence
 */

import { ref, computed } from 'vue'

// Default configuration
const DEFAULT_HOST = 'localhost'
const DEFAULT_PORT = 8000
const DEFAULT_PROTOCOL = 'http'

// Storage keys
const STORAGE_KEYS = {
  API_HOST: 'api_host',
  API_PORT: 'api_port', 
  API_PROTOCOL: 'api_protocol'
}

export function useApiConfig() {
  // Reactive configuration state
  const host = ref(localStorage.getItem(STORAGE_KEYS.API_HOST) || DEFAULT_HOST)
  const port = ref(parseInt(localStorage.getItem(STORAGE_KEYS.API_PORT) || DEFAULT_PORT.toString()))
  const protocol = ref(localStorage.getItem(STORAGE_KEYS.API_PROTOCOL) || DEFAULT_PROTOCOL)

  // Computed base URL
  const baseURL = computed(() => {
    return `${protocol.value}://${host.value}:${port.value}`
  })

  // Save configuration to localStorage
  function saveConfig() {
    localStorage.setItem(STORAGE_KEYS.API_HOST, host.value)
    localStorage.setItem(STORAGE_KEYS.API_PORT, port.value.toString())
    localStorage.setItem(STORAGE_KEYS.API_PROTOCOL, protocol.value)
  }

  // Reset to defaults
  function resetToDefaults() {
    host.value = DEFAULT_HOST
    port.value = DEFAULT_PORT
    protocol.value = DEFAULT_PROTOCOL
    saveConfig()
  }

  // Update configuration
  function updateConfig(newHost: string, newPort: number, newProtocol: string = 'http') {
    host.value = newHost.trim()
    port.value = newPort
    protocol.value = newProtocol
    saveConfig()
  }

  // Make API request with configured base URL
  async function apiRequest(endpoint: string, options: RequestInit = {}) {
    const url = `${baseURL.value}${endpoint}`
    
    const defaultOptions: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    }

    return fetch(url, { ...defaultOptions, ...options })
  }

  return {
    // State
    host,
    port, 
    protocol,
    baseURL,
    
    // Actions
    saveConfig,
    resetToDefaults,
    updateConfig,
    apiRequest
  }
}