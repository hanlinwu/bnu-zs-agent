import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

type ThemeMode = 'light' | 'dark'
type FontSize = 14 | 16 | 18 | 20

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(
    (localStorage.getItem('theme_mode') as ThemeMode) || 'light',
  )
  const fontSize = ref<FontSize>(
    (Number(localStorage.getItem('theme_font_size')) as FontSize) || 16,
  )

  function applyTheme() {
    document.documentElement.setAttribute('data-theme', mode.value)
    document.documentElement.style.fontSize = `${fontSize.value}px`
  }

  function toggleTheme() {
    mode.value = mode.value === 'light' ? 'dark' : 'light'
  }

  function setFontSize(size: FontSize) {
    fontSize.value = size
  }

  // Persist and apply on change
  watch(mode, (val) => {
    localStorage.setItem('theme_mode', val)
    applyTheme()
  })

  watch(fontSize, (val) => {
    localStorage.setItem('theme_font_size', String(val))
    applyTheme()
  })

  // Apply on store init
  applyTheme()

  return {
    mode,
    fontSize,
    toggleTheme,
    setFontSize,
  }
})
