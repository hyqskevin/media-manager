import { defineStore } from 'pinia'

const TOKEN_KEY = 'token'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY),
  }),
  actions: {
    setToken(token: string) {
      this.token = token
      localStorage.setItem(TOKEN_KEY, token)
    },
    /** v0.2 仅 admin 后端强制鉴权，前端对权限码一律放行 */
    hasPermission(_code: string | null): boolean {
      return true
    },
    clear() {
      this.token = null
      localStorage.removeItem(TOKEN_KEY)
    },
  },
})