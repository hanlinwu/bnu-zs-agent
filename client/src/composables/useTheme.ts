import { computed } from 'vue'
import { useThemeStore } from '@/stores/theme'

/**
 * Composable wrapper around the theme store.
 * Provides reactive theme state + system-preference detection.
 */
export function useTheme() {
  const store = useThemeStore()

  const isDark = computed(() => store.mode === 'dark')

  function toggleTheme() {
    store.toggleTheme()
  }

  function setFontSize(size: 14 | 16 | 18 | 20) {
    store.setFontSize(size)
  }

  function detectSystemPreference() {
    if (localStorage.getItem('theme_mode')) return // user has explicit preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    if (prefersDark && store.mode !== 'dark') {
      store.toggleTheme()
    }
  }

  // Listen for OS-level theme changes
  function watchSystemTheme() {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => {
      if (!localStorage.getItem('theme_mode')) {
        // Only auto-switch if user hasn't set an explicit preference
        if (e.matches && store.mode !== 'dark') store.toggleTheme()
        if (!e.matches && store.mode !== 'light') store.toggleTheme()
      }
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }

  return {
    mode: computed(() => store.mode),
    fontSize: computed(() => store.fontSize),
    isDark,
    toggleTheme,
    setFontSize,
    detectSystemPreference,
    watchSystemTheme,
  }
}
