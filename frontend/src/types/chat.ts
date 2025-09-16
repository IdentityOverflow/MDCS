/**
 * Chat-related TypeScript interfaces and types
 */

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  thinking?: string
  metadata?: {
    model?: string
    provider?: string
    tokens_used?: number
    response_time?: number
  }
  // Additional fields for persistence
  conversation_id?: string
  input_tokens?: number
  output_tokens?: number
  extra_data?: Record<string, any>
  created_at?: string
  updated_at?: string
}

export interface Conversation {
  id: string
  title: string
  persona_id?: string
  provider_type?: string
  provider_config?: Record<string, any>
  messages: ChatMessage[]
  created_at: string
  updated_at: string
}

export interface ChatRequest {
  message: string
  provider: 'ollama' | 'openai'
  stream: boolean
  chat_controls: Record<string, any>
  provider_settings?: Record<string, any>
  persona_id?: string
  conversation_id?: string
  session_id?: string
}

export interface ChatControls {
  provider: 'ollama' | 'openai'
  selected_model: string
  selectedPersonaId: string
  stream: boolean
  temperature: number
  max_tokens: number
  top_p: number
  frequency_penalty: number
  presence_penalty: number
  stop_sequences?: string[]
  seed?: number | null
  // Ollama specific
  repeat_penalty?: number | null
  top_k?: number | null
  // OpenAI specific  
  response_format?: 'text' | 'json_object' | null
  tool_choice?: 'none' | 'auto' | null
  parallel_tool_calls?: boolean | null
  // Allow for any additional properties from localStorage
  [key: string]: any
}

export type ProcessingStage = 'thinking' | 'generating' | 'complete' | null
export type ChatProvider = 'ollama' | 'openai'
export type MessageRole = 'user' | 'assistant' | 'system'