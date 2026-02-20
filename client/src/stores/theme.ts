import { defineStore } from 'pinia'
import { ref } from 'vue'

type ThemeMode = 'light' | 'dark'
type ThemePreference = 'light' | 'dark' | 'system'
type FontSize = 14 | 16 | 18 | 20

export const useThemeStore = defineStore('theme', () => {
  const savedPreference = localStorage.getItem('theme_preference') as ThemePreference | null
  const legacyMode = localStorage.getItem('theme_mode') as ThemeMode | null
  const themePreference = ref<ThemePreference>(
    savedPreference || legacyMode || 'light',
  )
  const mode = ref<ThemeMode>('light')
  const fontSize = ref<FontSize>(
    (Number(localStorage.getItem('theme_font_size')) as FontSize) || 16,
  )

  function resolveMode(preference: ThemePreference): ThemeMode {
    if (preference === 'system') {
      if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
        return 'dark'
      }
      return 'light'
    }
    return preference
  }

  function applyTheme() {
    document.documentElement.setAttribute('data-theme', mode.value)
    document.documentElement.style.fontSize = `${fontSize.value}px`
    const scale = fontSize.value / 16
    document.documentElement.style.setProperty('--font-scale', String(scale))
  }

  function toggleTheme(sourceEvent?: MouseEvent) {
    const nextMode: ThemeMode = mode.value === 'light' ? 'dark' : 'light'

    const supportsTransition = typeof document !== 'undefined' && 'startViewTransition' in document
    const prefersReducedMotion = typeof window !== 'undefined'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const shouldAnimate = Boolean(sourceEvent && supportsTransition && !prefersReducedMotion)

    if (!shouldAnimate) {
      themePreference.value = nextMode
      mode.value = nextMode
      localStorage.setItem('theme_preference', themePreference.value)
      localStorage.setItem('theme_mode', nextMode)
      applyTheme()
      return
    }

    const x = sourceEvent?.clientX ?? window.innerWidth / 2
    const y = sourceEvent?.clientY ?? window.innerHeight / 2
    const maxX = Math.max(x, window.innerWidth - x)
    const maxY = Math.max(y, window.innerHeight - y)
    const radius = Math.hypot(maxX, maxY)
    document.documentElement.style.setProperty('--theme-switch-x', `${x}px`)
    document.documentElement.style.setProperty('--theme-switch-y', `${y}px`)
    document.documentElement.style.setProperty('--theme-switch-r', `${radius}px`)

    const startViewTransition = (document as any).startViewTransition?.bind(document)
    if (typeof startViewTransition !== 'function') {
      themePreference.value = nextMode
      mode.value = nextMode
      localStorage.setItem('theme_preference', themePreference.value)
      localStorage.setItem('theme_mode', nextMode)
      applyTheme()
      return
    }

    startViewTransition(() => {
      themePreference.value = nextMode
      mode.value = nextMode
      localStorage.setItem('theme_preference', themePreference.value)
      localStorage.setItem('theme_mode', nextMode)
      applyTheme()
    })
  }

  function setThemePreference(preference: ThemePreference) {
    themePreference.value = preference
    mode.value = resolveMode(preference)
    localStorage.setItem('theme_preference', preference)
    if (preference === 'system') {
      localStorage.removeItem('theme_mode')
    } else {
      localStorage.setItem('theme_mode', preference)
    }
    applyTheme()
  }

  function setFontSize(size: FontSize) {
    fontSize.value = Number(size) as FontSize
    localStorage.setItem('theme_font_size', String(fontSize.value))
    applyTheme()
  }

  if (typeof window !== 'undefined' && window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    mq.addEventListener('change', () => {
      if (themePreference.value !== 'system') return
      mode.value = mq.matches ? 'dark' : 'light'
      applyTheme()
    })
  }

  // Apply on store init
  mode.value = resolveMode(themePreference.value)
  applyTheme()

  return {
    mode,
    themePreference,
    fontSize,
    toggleTheme,
    setThemePreference,
    setFontSize,
  }
})
