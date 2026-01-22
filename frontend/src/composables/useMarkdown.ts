/**
 * Composable for markdown parsing and rendering
 *
 * Uses marked.js with a custom renderer to generate clean, semantic HTML
 * that works well with the chat bubble layout and provides consistent spacing.
 */
import { marked } from 'marked'

/**
 * Configure marked with custom renderer and options
 * The renderer uses hooks to add semantic classes to HTML elements
 */
marked.use({
  breaks: true,        // Convert \n to <br> for better chat UX
  gfm: true,          // GitHub Flavored Markdown
  pedantic: false,    // Don't be too strict

  // Use hooks to modify HTML output
  hooks: {
    postprocess(html: string): string {
      // Add semantic classes to elements for consistent styling
      return html
        // Paragraphs
        .replace(/<p>/g, '<p class="md-paragraph">')
        // Headers
        .replace(/<h1>/g, '<h1 class="md-heading md-h1">')
        .replace(/<h2>/g, '<h2 class="md-heading md-h2">')
        .replace(/<h3>/g, '<h3 class="md-heading md-h3">')
        .replace(/<h4>/g, '<h4 class="md-heading md-h4">')
        .replace(/<h5>/g, '<h5 class="md-heading md-h5">')
        .replace(/<h6>/g, '<h6 class="md-heading md-h6">')
        // Lists
        .replace(/<ul>/g, '<ul class="md-list">')
        .replace(/<ol>/g, '<ol class="md-list">')
        .replace(/<li>/g, '<li class="md-list-item">')
        // Task lists (GitHub Flavored Markdown)
        .replace(/<li class="md-list-item"><input (disabled="" )?type="checkbox"/g, '<li class="md-list-item md-task-item"><input class="md-task-checkbox" $1type="checkbox"')
        // Code blocks
        .replace(/<pre>/g, '<div class="md-code-block"><pre>')
        .replace(/<\/pre>/g, '</pre></div>')
        .replace(/<code>/g, '<code class="md-inline-code">')
        .replace(/<pre><code class="md-inline-code"/g, '<pre><code') // Fix for code blocks
        // Blockquotes
        .replace(/<blockquote>/g, '<blockquote class="md-blockquote">')
        // Links - add security attributes
        .replace(/<a href="http/g, '<a class="md-link" rel="noopener noreferrer" href="http')
        .replace(/<a href="(?!http)/g, '<a class="md-link" href="')
        // Strong and emphasis
        .replace(/<strong>/g, '<strong class="md-strong">')
        .replace(/<em>/g, '<em class="md-em">')
        // Horizontal rule
        .replace(/<hr>/g, '<hr class="md-hr">')
        .replace(/<hr \/>/g, '<hr class="md-hr" />')
    }
  }
})

export function useMarkdown() {
  /**
   * Parse markdown text to HTML with custom rendering
   *
   * @param text - Raw markdown text
   * @returns Parsed HTML with semantic classes
   */
  const parseMarkdown = (text: string): string => {
    if (!text) return ''

    try {
      // marked() now uses our custom renderer
      return marked(text) as string
    } catch (error) {
      console.error('Failed to parse markdown:', error)
      // Fallback: escape HTML and convert newlines to breaks
      const escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>')
      return escaped
    }
  }

  /**
   * Check if text contains markdown syntax
   *
   * @param text - Text to check
   * @returns True if markdown patterns are detected
   */
  const hasMarkdown = (text: string): boolean => {
    if (!text) return false

    // Regex patterns for common markdown syntax
    const markdownPatterns = [
      /\*\*.*?\*\*/,     // Bold
      /\*.*?\*/,         // Italic
      /`.*?`/,           // Inline code
      /^#+ /m,           // Headers
      /^\* /m,           // Bullet lists
      /^- /m,            // Alternative bullet lists
      /^\d+\. /m,        // Numbered lists
      /\[.*?\]\(.*?\)/,  // Links
      /^```/m,           // Code blocks
      /^> /m,            // Blockquotes
      /^---$/m,          // Horizontal rules
      /\[[ x]\]/         // Task lists
    ]

    return markdownPatterns.some(pattern => pattern.test(text))
  }

  /**
   * Strip all markdown formatting and return plain text
   * Useful for previews or search
   *
   * @param text - Markdown text
   * @returns Plain text without formatting
   */
  const stripMarkdown = (text: string): string => {
    if (!text) return ''

    return text
      .replace(/```[\s\S]*?```/g, '') // Remove code blocks
      .replace(/`([^`]+)`/g, '$1')    // Remove inline code
      .replace(/\*\*([^*]+)\*\*/g, '$1') // Remove bold
      .replace(/\*([^*]+)\*/g, '$1')  // Remove italic
      .replace(/^#+\s+/gm, '')        // Remove headers
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Convert links to text
      .replace(/^[>-]\s+/gm, '')      // Remove quotes and list markers
      .trim()
  }

  return {
    parseMarkdown,
    hasMarkdown,
    stripMarkdown
  }
}