import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({
  gfm: true,
  breaks: true,
})

const renderer = new marked.Renderer()
renderer.link = ({ href, title, tokens }) => {
  const safeHref = href || ''
  const text = tokens.map(t => ('raw' in t ? t.raw : '')).join('')
  const titleAttr = title ? ` title="${title}"` : ''
  return `<a href="${safeHref}" target="_blank" rel="noopener noreferrer nofollow"${titleAttr}>${text}</a>`
}
marked.use({ renderer })

function normalizeThinkBlocks(text: string): string {
  if (!text || !text.includes('<think>')) return text
  return text.replace(/<think>([\s\S]*?)<\/think>/gi, (_raw, content: string) => {
    const sentence = (content || '').replace(/\s+/g, ' ').trim()
    if (!sentence) return ''
    return [
      '',
      '<details class="think-block">',
      '<summary>思考结果</summary>',
      '',
      sentence,
      '',
      '</details>',
      '',
    ].join('\n')
  })
}

export function renderMarkdown(text: string): string {
  const input = normalizeThinkBlocks(text || '')
  const html = marked.parse(input) as string
  return DOMPurify.sanitize(html)
}
