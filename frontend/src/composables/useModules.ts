/**
 * Modules Management Composable
 * Provides CRUD operations for modules with API integration
 */

import { ref, computed } from 'vue'
import { useApiConfig } from '@/composables/apiConfig'
import type { Module, ModuleCreateRequest, ModuleUpdateRequest } from '@/types'

// Global state for modules (could be moved to Pinia store later)
const modules = ref<Module[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

export function useModules() {
  const apiConfig = useApiConfig()

  // Computed properties
  const simpleModules = computed(() => 
    modules.value.filter(module => module.type === 'simple')
  )

  const advancedModules = computed(() => 
    modules.value.filter(module => module.type === 'advanced')
  )

  const activeModules = computed(() => 
    modules.value.filter(module => module.is_active)
  )

  // Helper function for API requests
  async function makeRequest(endpoint: string, options: RequestInit = {}) {
    try {
      const response = await apiConfig.apiRequest(endpoint, options)
      
      if (!response.ok) {
        const errorData = await response.text()
        let errorMessage: string
        
        try {
          const errorJson = JSON.parse(errorData)
          errorMessage = errorJson.detail || `HTTP ${response.status}`
        } catch {
          errorMessage = `HTTP ${response.status}: ${errorData}`
        }
        
        throw new Error(errorMessage)
      }
      
      // Handle 204 No Content responses (delete)
      if (response.status === 204) {
        return null
      }
      
      return await response.json()
    } catch (err) {
      console.error('API request failed:', err)
      throw err
    }
  }

  // API Functions
  
  /**
   * Fetch all modules from the server
   */
  async function fetchModules(type?: 'simple' | 'advanced'): Promise<void> {
    loading.value = true
    error.value = null
    
    try {
      const queryParams = new URLSearchParams()
      if (type) {
        queryParams.append('type', type)
      }
      
      const endpoint = `/api/modules${queryParams.toString() ? '?' + queryParams.toString() : ''}`
      const response = await makeRequest(endpoint)
      
      modules.value = response || []
      console.log(`Fetched ${modules.value.length} modules`)
      
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch modules'
      console.error('Error fetching modules:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * Get a specific module by ID
   */
  async function getModule(id: string): Promise<Module | null> {
    loading.value = true
    error.value = null
    
    try {
      const response = await makeRequest(`/api/modules/${id}`)
      return response as Module
      
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to get module'
      console.error('Error getting module:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Create a new module
   */
  async function createModule(moduleData: ModuleCreateRequest): Promise<Module | null> {
    loading.value = true
    error.value = null
    
    try {
      const response = await makeRequest('/api/modules', {
        method: 'POST',
        body: JSON.stringify(moduleData)
      })
      
      const newModule = response as Module
      
      // Add to local state
      modules.value.unshift(newModule) // Add to beginning (newest first)
      
      console.log('Created module:', newModule.id)
      return newModule
      
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create module'
      console.error('Error creating module:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Update an existing module
   */
  async function updateModule(id: string, updateData: ModuleUpdateRequest): Promise<Module | null> {
    loading.value = true
    error.value = null
    
    try {
      const response = await makeRequest(`/api/modules/${id}`, {
        method: 'PUT',
        body: JSON.stringify(updateData)
      })
      
      const updatedModule = response as Module
      
      // Update in local state
      const index = modules.value.findIndex(module => module.id === id)
      if (index !== -1) {
        modules.value[index] = updatedModule
      }
      
      console.log('Updated module:', id)
      return updatedModule
      
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update module'
      console.error('Error updating module:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete a module
   */
  async function deleteModule(id: string): Promise<boolean> {
    loading.value = true
    error.value = null
    
    try {
      await makeRequest(`/api/modules/${id}`, {
        method: 'DELETE'
      })
      
      // Remove from local state
      modules.value = modules.value.filter(module => module.id !== id)
      
      console.log('Deleted module:', id)
      return true
      
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete module'
      console.error('Error deleting module:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Clear error state
   */
  function clearError(): void {
    error.value = null
  }

  /**
   * Refresh modules list
   */
  async function refreshModules(): Promise<void> {
    await fetchModules()
  }

  return {
    // State
    modules: computed(() => modules.value),
    simpleModules,
    advancedModules,
    activeModules,
    loading: computed(() => loading.value),
    error: computed(() => error.value),
    
    // Actions
    fetchModules,
    getModule,
    createModule,
    updateModule,
    deleteModule,
    clearError,
    refreshModules
  }
}