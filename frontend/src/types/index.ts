// Shared TypeScript interfaces

// Execution context enum for modules
export type ExecutionContext = 'IMMEDIATE' | 'POST_RESPONSE' | 'ON_DEMAND'

// Module type enum
export type ModuleType = 'simple' | 'advanced'

// Helper type for execution stage information
export interface ExecutionStageInfo {
  stage: number
  name: string
  description: string
}

export interface Persona {
  id: string
  name: string
  description: string | null
  template: string
  mode: 'autonomous' | 'reactive'
  loop_frequency: string | null
  first_message: string | null
  image_path: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Module {
  id: string
  name: string
  description: string | null
  content: string | null
  type: ModuleType
  trigger_pattern: string | null
  script: string | null
  execution_context: ExecutionContext | null
  requires_ai_inference: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ModuleCreateRequest {
  name: string
  description?: string
  content?: string
  type: ModuleType
  trigger_pattern?: string
  script?: string
  execution_context?: ExecutionContext
}

export interface ModuleUpdateRequest {
  name?: string
  description?: string
  content?: string
  type?: ModuleType
  trigger_pattern?: string
  script?: string
  execution_context?: ExecutionContext
}

export interface PersonaCreateRequest {
  name: string
  description?: string
  template: string
  mode: 'autonomous' | 'reactive'
  loop_frequency?: string
  first_message?: string
  image_path?: string
}

export interface PersonaUpdateRequest {
  name?: string
  description?: string
  template?: string
  mode?: 'autonomous' | 'reactive'
  loop_frequency?: string
  first_message?: string
  image_path?: string
}