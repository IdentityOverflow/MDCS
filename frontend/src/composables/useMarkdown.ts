/**
 * Composable for markdown parsing and rendering
 */
import { marked } from 'marked'

// Configure marked with safe defaults
marked.setOptions({
  breaks: true,        // Convert \n to <br> (this should handle single line breaks)
  gfm: true,          // GitHub Flavored Markdown
  headerIds: false,   // Don't generate header IDs
  mangle: false,      // Don't escape autolinked email addresses
  sanitize: false     // We'll handle XSS prevention at template level
})

export function useMarkdown() {
  /**
   * Parse markdown text to HTML
   */
  const parseMarkdown = (text: string): string => {
    if (!text) return ''
    
    try {
      // First, let marked parse the markdown normally
      const result = marked(text) as string
      
      // Then post-process to add breaks for empty lines that might have been lost
      // This preserves the markdown parsing while adding empty line spacing
      const finalResult = result
        .replace(/<\/p>\s*<p>/g, '</p><br><p>')  // Add break between paragraphs
        .replace(/<\/ul>\s*<p>/g, '</ul><br><p>')  // Add break after lists to paragraphs
        .replace(/<\/h[1-6]>\s*<p>/g, (match) => match.replace('><p>', '><br><p>'))  // Add break after headers to paragraphs
        
      return finalResult
    } catch (error) {
      console.error('Failed to parse markdown:', error)
      return text.replace(/\n/g, '<br>') // Fallback with line breaks
    }
  }

  /**
   * Check if text contains markdown syntax
   */
  const hasMarkdown = (text: string): boolean => {
    if (!text) return false
    
    // Simple regex to detect common markdown patterns
    const markdownPatterns = [
      /\*\*.*?\*\*/,     // Bold
      /\*.*?\*/,         // Italic
      /`.*?`/,           // Inline code
      /^#+ /m,           // Headers
      /^\* /m,           // Bullet lists
      /^\d+\. /m,        // Numbered lists
      /\[.*?\]\(.*?\)/,  // Links
      /^```/m,           // Code blocks
      /^\> /m            // Blockquotes
    ]
    
    return markdownPatterns.some(pattern => pattern.test(text))
  }

  return {
    parseMarkdown,
    hasMarkdown
  }
}