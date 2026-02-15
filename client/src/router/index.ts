import { createRouter, createWebHistory } from 'vue-router'
import { userRoutes } from './user'
import { adminRoutes } from './admin'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    ...userRoutes,
    ...adminRoutes,
  ],
})

// Global guards: check token, check admin RBAC for /admin/* routes
router.beforeEach(async (to, _from, next) => {
  const whiteList = ['/login', '/admin/login']
  if (whiteList.includes(to.path)) return next()

  // Check user token from localStorage
  const token = localStorage.getItem('token')
  if (!token) return next('/login')

  // Admin routes need admin token
  if (to.path.startsWith('/admin')) {
    const adminToken = localStorage.getItem('admin_token')
    if (!adminToken) return next('/admin/login')
  }

  next()
})

export default router
