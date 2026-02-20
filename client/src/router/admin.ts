import type { RouteRecordRaw } from 'vue-router'

export const adminRoutes: RouteRecordRaw[] = [
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: () => import('@/views/admin/AdminLogin.vue'),
    meta: { title: '管理员登录', requiresAuth: false },
  },
  {
    path: '/admin',
    component: () => import('@/views/admin/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    redirect: '/admin/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: () => import('@/views/admin/Dashboard.vue'),
        meta: { title: '管理面板', keepAlive: true },
      },
      {
        path: 'knowledge',
        name: 'AdminKnowledge',
        component: () => import('@/views/admin/Knowledge.vue'),
        meta: { title: '知识库管理' },
      },
      {
        path: 'knowledge/review',
        name: 'AdminKnowledgeReview',
        component: () => import('@/views/admin/KnowledgeReview.vue'),
        meta: { title: '知识库审核' },
      },
      {
        path: 'sensitive',
        name: 'AdminSensitive',
        component: () => import('@/views/admin/Sensitive.vue'),
        meta: { title: '敏感词管理' },
      },
      {
        path: 'model',
        name: 'AdminModel',
        component: () => import('@/views/admin/Model.vue'),
        meta: { title: '模型管理' },
      },
      {
        path: 'system-config',
        name: 'AdminSystemConfig',
        component: () => import('@/views/admin/SystemConfig.vue'),
        meta: { title: '风险与Prompt配置' },
      },
      {
        path: 'system-settings',
        name: 'AdminSystemSettings',
        component: () => import('@/views/admin/SystemSettings.vue'),
        meta: { title: '系统设置' },
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('@/views/admin/Users.vue'),
        meta: { title: '用户管理', keepAlive: true },
      },
      {
        path: 'conversations',
        name: 'AdminConversations',
        component: () => import('@/views/admin/Conversations.vue'),
        meta: { title: '对话日志', keepAlive: true },
      },
      {
        path: 'admins',
        name: 'AdminAdmins',
        component: () => import('@/views/admin/Admins.vue'),
        meta: { title: '管理员管理' },
      },
      {
        path: 'roles',
        name: 'AdminRoles',
        component: () => import('@/views/admin/Roles.vue'),
        meta: { title: '角色管理' },
      },
      {
        path: 'workflows',
        name: 'AdminWorkflows',
        component: () => import('@/views/admin/Workflows.vue'),
        meta: { title: '工作流管理' },
      },
      {
        path: 'media',
        name: 'AdminMedia',
        component: () => import('@/views/admin/Media.vue'),
        meta: { title: '素材库管理' },
      },
      {
        path: 'calendar',
        name: 'AdminCalendar',
        component: () => import('@/views/admin/Calendar.vue'),
        meta: { title: '招生日历' },
      },
      {
        path: 'logs',
        name: 'AdminLogs',
        component: () => import('@/views/admin/Logs.vue'),
        meta: { title: '审计日志' },
      },
      {
        path: 'profile',
        name: 'AdminProfile',
        component: () => import('@/views/admin/Profile.vue'),
        meta: { title: '个人信息' },
      },
    ],
  },
]
