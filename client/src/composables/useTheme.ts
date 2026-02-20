import { computed } from 'vue'
import { useThemeStore } from '@/stores/theme'

/**
 * Composable wrapper around the theme store.
 * Provides reactive theme state + system-preference detection.
 */
export function useTheme() {
  const store = useThemeStore()

  const isDark = computed(() => store.mode === 'dark')

  function toggleTheme(e?: MouseEvent) {
    store.toggleTheme(e)
  }

  function setThemePreference(mode: 'light' | 'dark' | 'system') {
    store.setThemePreference(mode)
  }

  function setFontSize(size: 14 | 16 | 18 | 20) {
    store.setFontSize(size)
  }

  return {
    mode: computed(() => store.mode),
    themePreference: computed(() => store.themePreference),
    fontSize: computed(() => store.fontSize),
    isDark,
    toggleTheme,
    setThemePreference,
    setFontSize,
  }
}
