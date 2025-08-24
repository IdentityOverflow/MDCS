<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { EditorView, basicSetup } from 'codemirror'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'
import { EditorState } from '@codemirror/state'

const props = defineProps<{
  modelValue: string | undefined
  placeholder?: string
  readonly?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const editorContainer = ref<HTMLDivElement>()
let view: EditorView | null = null

// Custom theme to match cyberpunk styling
const cyberpunkTheme = EditorView.theme({
  '&': {
    color: '#00ffff',
    backgroundColor: '#1a1a2e',
    fontSize: '14px',
    fontFamily: "'Fira Code', 'JetBrains Mono', monospace",
  },
  '.cm-content': {
    padding: '12px',
    minHeight: '120px',
    caretColor: '#00ffff',
  },
  '.cm-focused .cm-content': {
    outline: 'none',
  },
  '.cm-editor': {
    borderRadius: '2px',
    border: '1px solid rgba(0, 212, 255, 0.2)',
    transition: 'border-color 0.2s ease',
  },
  '.cm-editor.cm-focused': {
    borderColor: '#ff006e',
    boxShadow: '0 0 0 2px rgba(0, 212, 255, 0.1)',
  },
  '.cm-placeholder': {
    color: 'rgba(0, 255, 255, 0.5)',
  },
  '.cm-cursor': {
    borderLeftColor: '#00ffff',
  },
  '.cm-selectionBackground': {
    backgroundColor: 'rgba(0, 212, 255, 0.2) !important',
  },
  '.cm-focused .cm-selectionBackground': {
    backgroundColor: 'rgba(0, 212, 255, 0.3) !important',
  },
  '.cm-activeLine': {
    backgroundColor: 'rgba(0, 212, 255, 0.05)',
  },
  '.cm-activeLineGutter': {
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
  },
  '.cm-gutters': {
    backgroundColor: '#16213e',
    borderRight: '1px solid rgba(0, 212, 255, 0.2)',
    color: 'rgba(0, 255, 255, 0.4)',
  },
  '.cm-lineNumbers': {
    color: 'rgba(0, 255, 255, 0.4)',
  },
  '.cm-foldGutter': {
    color: 'rgba(0, 255, 255, 0.4)',
  }
}, { dark: true })

// Initialize editor
onMounted(() => {
  if (!editorContainer.value) return

  const updateListener = EditorView.updateListener.of((update) => {
    if (update.docChanged) {
      const newValue = update.state.doc.toString()
      if (newValue !== props.modelValue) {
        emit('update:modelValue', newValue)
      }
    }
  })

  const extensions = [
    basicSetup,
    python(),
    cyberpunkTheme,
    updateListener,
    EditorView.lineWrapping,
  ]

  // Add readonly extension if needed
  if (props.readonly) {
    extensions.push(EditorState.readOnly.of(true))
  }

  const state = EditorState.create({
    doc: props.modelValue || '',
    extensions
  })

  view = new EditorView({
    state,
    parent: editorContainer.value
  })
})

// Watch for prop changes
watch(() => props.modelValue, (newValue) => {
  if (view && view.state.doc.toString() !== newValue) {
    const transaction = view.state.update({
      changes: { from: 0, to: view.state.doc.length, insert: newValue || '' }
    })
    view.dispatch(transaction)
  }
})

// Cleanup
onUnmounted(() => {
  if (view) {
    view.destroy()
    view = null
  }
})

// Focus method for external access
defineExpose({
  focus: () => view?.focus()
})
</script>

<template>
  <div class="code-editor">
    <div ref="editorContainer" class="editor-container"></div>
  </div>
</template>

<style scoped>
.code-editor {
  position: relative;
  width: 100%;
}

.editor-container {
  width: 100%;
}

/* Ensure CodeMirror fills the container */
.editor-container :deep(.cm-editor) {
  width: 100%;
  min-height: 120px;
}

.editor-container :deep(.cm-scroller) {
  font-family: 'Fira Code', 'JetBrains Mono', 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

/* Syntax highlighting theme adjustments for cyberpunk */
.editor-container :deep(.cm-content) {
  --hl-keyword: #ff006e;
  --hl-string: #00ff41;
  --hl-comment: rgba(0, 255, 255, 0.6);
  --hl-number: #ffa500;
  --hl-function: #00d4ff;
  --hl-variable: #00ffff;
}

.editor-container :deep(.tok-keyword) {
  color: var(--hl-keyword) !important;
  font-weight: 600;
}

.editor-container :deep(.tok-string) {
  color: var(--hl-string) !important;
}

.editor-container :deep(.tok-comment) {
  color: var(--hl-comment) !important;
  font-style: italic;
}

.editor-container :deep(.tok-number) {
  color: var(--hl-number) !important;
}

.editor-container :deep(.tok-variableName) {
  color: var(--hl-variable) !important;
}

.editor-container :deep(.tok-function) {
  color: var(--hl-function) !important;
  font-weight: 600;
}

.editor-container :deep(.tok-operator) {
  color: #ff006e !important;
}

.editor-container :deep(.tok-bracket) {
  color: rgba(0, 255, 255, 0.8) !important;
}

.editor-container :deep(.tok-className) {
  color: #00d4ff !important;
  font-weight: 600;
}

.editor-container :deep(.tok-definition) {
  color: #00ffff !important;
  font-weight: 600;
}
</style>