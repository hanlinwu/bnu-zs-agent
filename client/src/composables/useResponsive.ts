import { ref, onMounted, onUnmounted } from 'vue'

export type Breakpoint = 'mobile' | 'tablet' | 'desktop' | 'wide'

const BREAKPOINTS = {
  mobile: 0,
  tablet: 768,
  desktop: 1024,
  wide: 1440,
} as const

/**
 * Composable for responsive breakpoint detection.
 * Provides reactive current breakpoint and boolean helpers.
 */
export function useResponsive() {
  const width = ref(typeof window !== 'undefined' ? window.innerWidth : 1024)
  const breakpoint = ref<Breakpoint>(getBreakpoint(width.value))
  const isMobile = ref(width.value < BREAKPOINTS.tablet)
  const isTablet = ref(
    width.value >= BREAKPOINTS.tablet && width.value < BREAKPOINTS.desktop,
  )
  const isDesktop = ref(width.value >= BREAKPOINTS.desktop)

  function getBreakpoint(w: number): Breakpoint {
    if (w >= BREAKPOINTS.wide) return 'wide'
    if (w >= BREAKPOINTS.desktop) return 'desktop'
    if (w >= BREAKPOINTS.tablet) return 'tablet'
    return 'mobile'
  }

  function update() {
    width.value = window.innerWidth
    breakpoint.value = getBreakpoint(width.value)
    isMobile.value = width.value < BREAKPOINTS.tablet
    isTablet.value =
      width.value >= BREAKPOINTS.tablet && width.value < BREAKPOINTS.desktop
    isDesktop.value = width.value >= BREAKPOINTS.desktop
  }

  let resizeTimer: ReturnType<typeof setTimeout> | null = null
  function onResize() {
    if (resizeTimer) clearTimeout(resizeTimer)
    resizeTimer = setTimeout(update, 100)
  }

  onMounted(() => {
    update()
    window.addEventListener('resize', onResize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', onResize)
    if (resizeTimer) clearTimeout(resizeTimer)
  })

  return {
    width,
    breakpoint,
    isMobile,
    isTablet,
    isDesktop,
  }
}
