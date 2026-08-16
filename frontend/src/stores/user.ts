import { defineStore } from 'pinia'

interface JwtPayload {
  sub: string
  role?: string
  permissions?: string[]
}

function parseJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const payload = JSON.parse(atob(parts[1]))
    return payload as JwtPayload
  } catch {
    return null
  }
}

function readRoleFromStorage(): 'admin' | 'editor' | null {
  const token = localStorage.getItem('token')
  if (!token) return null
  const payload = parseJwtPayload(token)
  const r = payload?.role
  return r === 'admin' || r === 'editor' ? r : null
}

function readPermissionsFromStorage(): string[] {
  const token = localStorage.getItem('token')
  if (!token) return []
  const payload = parseJwtPayload(token)
  return Array.isArray(payload?.permissions) ? payload!.permissions! : []
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: null as string | null,
    role: null as 'admin' | 'editor' | null,
    permissions: [] as string[],
  }),
  getters: {
    /** 优先用 store 状态；page refresh 后 store 未初始化时退到 localStorage 解析 token */
    isAdmin(): boolean {
      if (this.role === 'admin') return true
      return readRoleFromStorage() === 'admin'
    },
    isAuthenticated(): boolean {
      if (this.token !== null) return true
      return !!localStorage.getItem('token')
    },
    /** 是否具备指定权限码。`*` 通配。后端 require_permission / require_admin 与之一致。 */
    hasPermission(): (code: string) => boolean {
      const perms = this.permissions.length ? this.permissions : readPermissionsFromStorage()
      const set = new Set(perms)
      return (code: string) => set.has('*') || set.has(code)
    },
  },
  actions: {
    setToken(token: string) {
      this.token = token
      const payload = parseJwtPayload(token)
      const r = payload?.role
      if (r === 'admin' || r === 'editor') {
        this.role = r
      } else {
        this.role = null
      }
      this.permissions = Array.isArray(payload?.permissions) ? payload!.permissions! : []
    },
    clear() {
      this.token = null
      this.role = null
      this.permissions = []
      localStorage.removeItem('token')
    },
  },
})