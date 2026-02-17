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

export function renderMarkdown(text: string): string {
  const input = text || ''
  const html = marked.parse(input) as string
  return DOMPurify.sanitize(html)
}
