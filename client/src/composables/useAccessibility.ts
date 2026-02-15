import { ref, onMounted, onUnmounted } from 'vue'

/**
 * Composable for accessibility helpers:
 * - Reduced motion detection
 * - High contrast mode detection
 * - Screen reader announcement
 * - Keyboard navigation mode tracking
 */
export function useAccessibility() {
  const prefersReducedMotion = ref(false)
  const prefersHighContrast = ref(false)
  const isKeyboardNav = ref(false)

  let cleanups: (() => void)[] = []

  function announce(message: string, priority: 'polite' | 'assertive' = 'polite') {
    let el = document.getElementById('a11y-live-region')
    if (!el) {
      el = document.createElement('div')
      el.id = 'a11y-live-region'
      el.setAttribute('aria-live', priority)
      el.setAttribute('aria-atomic', 'true')
      el.className = 'sr-only'
      document.body.appendChild(el)
    }
    el.setAttribute('aria-live', priority)
    el.textContent = ''
    // Use timeout to ensure screen readers pick up the change
    setTimeout(() => {
      el!.textContent = message
    }, 50)
  }

  onMounted(() => {
    // Reduced motion
    const motionMq = window.matchMedia('(prefers-reduced-motion: reduce)')
    prefersReducedMotion.value = motionMq.matches
    const motionHandler = (e: MediaQueryListEvent) => {
      prefersReducedMotion.value = e.matches
    }
    motionMq.addEventListener('change', motionHandler)
    cleanups.push(() => motionMq.removeEventListener('change', motionHandler))

    // High contrast
    const contrastMq = window.matchMedia('(prefers-contrast: more)')
    prefersHighContrast.value = contrastMq.matches
    const contrastHandler = (e: MediaQueryListEvent) => {
      prefersHighContrast.value = e.matches
    }
    contrastMq.addEventListener('change', contrastHandler)
    cleanups.push(() => contrastMq.removeEventListener('change', contrastHandler))

    // Keyboard vs mouse navigation
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Tab') isKeyboardNav.value = true
    }
    const mouseHandler = () => {
      isKeyboardNav.value = false
    }
    document.addEventListener('keydown', keyHandler)
    document.addEventListener('mousedown', mouseHandler)
    cleanups.push(() => {
      document.removeEventListener('keydown', keyHandler)
      document.removeEventListener('mousedown', mouseHandler)
    })
  })

  onUnmounted(() => {
    cleanups.forEach((fn) => fn())
    cleanups = []
  })

  return {
    prefersReducedMotion,
    prefersHighContrast,
    isKeyboardNav,
    announce,
  }
}
