import { createRouter, createWebHistory } from 'vue-router'
import { ref } from 'vue'
import { userRoutes } from './user'
import { adminRoutes } from './admin'

/** Reactive loading flag — used by App.vue to show/hide progress bar */
export const routeLoading = ref(false)

const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...userRoutes,
    ...adminRoutes,
  ],
})

// Global guards: check token and trigger profile hydration lazily
router.beforeEach(async (to, _from, next) => {
  routeLoading.value = true

  const whiteList = ['/login', '/admin/login']
  if (whiteList.includes(to.path)) return next()

  // Admin routes use admin_token
  if (to.path.startsWith('/admin')) {
    const adminToken = localStorage.getItem('admin_token')
    if (!adminToken) return next('/admin/login')
    return next()
  }

  // User routes use token
  const token = localStorage.getItem('token')
  if (!token) return next('/login')

  // Ensure user profile is loaded without blocking navigation
  const { useUserStore } = await import('@/stores/user')
  const userStore = useUserStore()
  if (!userStore.userInfo) {
    void userStore.fetchProfile().catch(() => {
      userStore.logout()
      if (router.currentRoute.value.path !== '/login') {
        router.replace('/login')
      }
    })
  }

  next()
})

router.afterEach(() => {
  routeLoading.value = false
})

router.onError(() => {
  routeLoading.value = false
})

export default router
