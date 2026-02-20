/** 用户角色 */
export type UserRole = 'gaokao' | 'kaoyan' | 'international' | 'parent'

/** 管理员角色 */
export type AdminRole = 'super_admin' | 'content_reviewer' | 'admin' | 'teacher'

/** 普通用户 */
export interface User {
  id: string
  phone: string
  nickname: string
  avatar?: string
  role: UserRole
  createdAt: string
  updatedAt: string
}

/** 管理员用户 */
export interface AdminUser {
  id: string
  username: string
  phone: string
  nickname: string
  avatar?: string
  adminRole: AdminRole
  permissions: string[]
  enabled: boolean
  lastLoginAt?: string
  lastLoginIp?: string
  createdAt: string
  updatedAt: string
}

/** 用户资料更新参数 */
export interface UpdateProfileParams {
  nickname?: string
  avatar?: string
  role?: UserRole
}

/** 登录参数 */
export interface LoginParams {
  phone: string
  code: string
  nickname?: string
  userRole?: UserRole
}

/** 登录响应 */
export interface LoginResult {
  token: string
  user: User
}
