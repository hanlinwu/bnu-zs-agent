/**
 * Generate a deterministic default avatar data URL based on a name string.
 * Returns an SVG with a colored background and the first character of the name.
 */

const AVATAR_COLORS = [
  '#003DA5', '#1A5FBF', '#2E7D32', '#C4972F', '#C62828',
  '#6A1B9A', '#00838F', '#AD1457', '#4E342E', '#37474F',
]

function hashCode(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0
  }
  return Math.abs(hash)
}

export function generateAvatar(name: string): string {
  const initial = (name || '?').charAt(0).toUpperCase()
  const color = AVATAR_COLORS[hashCode(name || '') % AVATAR_COLORS.length]
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
    <rect width="64" height="64" rx="8" fill="${color}"/>
    <text x="32" y="40" text-anchor="middle" fill="#fff" font-size="28" font-weight="600" font-family="system-ui,sans-serif">${initial}</text>
  </svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}
